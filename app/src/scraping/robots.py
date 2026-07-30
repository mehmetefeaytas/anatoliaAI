"""robots.txt çekme, ayrıştırma ve raporlama — CLAUDE.md §14 uyumu.

İlgili: ../../concepts/web-scraping.md, ../../decisions/python-tabanli-veri-toplama.md

Varsayılan davranış **UYUM**: robots.txt bir yolu yasaklıyorsa o URL çekilmez ve
raporda "robots disallow" olarak görünür. `--ignore-robots` CLI bayrağı denetimi
devre dışı bırakabilir ama varsayılan kapalıdır; bayrak açıkken bile karar
raporlanır (sessizce ihlal yok).

Saf stdlib: `urllib` dışında bağımlılık yok. HTTP çekimi enjekte edilebilir
(`fetcher`), böylece testler ağa çıkmadan koşar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional
from urllib.parse import urlsplit, urlunsplit

# (status_code, body) döndüren çekici; None body = çekilemedi
Fetcher = Callable[[str], tuple[Optional[int], Optional[str]]]

DEFAULT_USER_AGENT = "AnatoliaAI-Research/1.0 (+TEKNOFEST 2026; arastirma amacli)"


@dataclass(frozen=True)
class RobotsRule:
    """Tek bir Allow/Disallow satırı."""

    allow: bool
    pattern: str

    @property
    def specificity(self) -> int:
        """Uzun desen daha spesifiktir (REP: en uzun eşleşme kazanır)."""
        return len(self.pattern)


@dataclass
class RobotsPolicy:
    """Bir origin (şema+host) için robots.txt kararı."""

    origin: str
    status: Optional[int] = None
    fetched: bool = False
    error: Optional[str] = None
    rules: list[RobotsRule] = field(default_factory=list)
    sitemaps: list[str] = field(default_factory=list)
    crawl_delay: Optional[float] = None
    matched_agent: Optional[str] = None

    def allows(self, url: str) -> bool:
        """URL'in yol+sorgu kısmı için izin kararı.

        robots.txt yoksa/çekilemediyse REP gereği **izin var** sayılır.
        """
        if not self.rules:
            return True
        target = _path_of(url)
        best: Optional[RobotsRule] = None
        for rule in self.rules:
            if not _pattern_matches(rule.pattern, target):
                continue
            if best is None:
                best = rule
                continue
            if rule.specificity > best.specificity:
                best = rule
            elif rule.specificity == best.specificity and rule.allow:
                # eşit uzunlukta Allow, Disallow'u yener (Google REP)
                best = rule
        return True if best is None else best.allow

    def reason(self, url: str) -> str:
        """Kararın insan-okur gerekçesi (rapor için)."""
        if not self.fetched:
            return f"robots.txt cekilemedi ({self.error or self.status}) — REP: izin varsayildi"
        if not self.rules:
            return "robots.txt kural icermiyor — izin"
        return "izin" if self.allows(url) else "robots.txt Disallow"

    def summary(self) -> str:
        """Toplama raporuna yazılacak tek satırlık özet."""
        if not self.fetched:
            return f"cekilemedi ({self.error or self.status}); REP geregi izin varsayildi"
        n_dis = sum(1 for r in self.rules if not r.allow)
        n_all = sum(1 for r in self.rules if r.allow)
        parts = [f"HTTP {self.status}", f"{n_all} Allow / {n_dis} Disallow"]
        if self.matched_agent:
            parts.append(f"agent='{self.matched_agent}'")
        if self.crawl_delay is not None:
            parts.append(f"crawl-delay={self.crawl_delay}s")
        if self.sitemaps:
            parts.append(f"{len(self.sitemaps)} sitemap")
        return "; ".join(parts)


def origin_of(url: str) -> str:
    """URL'den şema+host çıkarır (robots.txt origin başına tekildir)."""
    p = urlsplit(url)
    return urlunsplit((p.scheme or "https", p.netloc, "", "", ""))


def _path_of(url: str) -> str:
    p = urlsplit(url)
    path = p.path or "/"
    return f"{path}?{p.query}" if p.query else path


def _pattern_matches(pattern: str, target: str) -> bool:
    """robots.txt joker desenini (`*`, sonda `$`) yol ile eşleştirir."""
    anchored_end = pattern.endswith("$")
    body = pattern[:-1] if anchored_end else pattern
    regex = "".join(".*" if ch == "*" else re.escape(ch) for ch in body)
    return re.match(regex + ("$" if anchored_end else ""), target) is not None


def parse_robots(text: str, user_agent: str) -> tuple[list[RobotsRule], list[str],
                                                      Optional[float], Optional[str]]:
    """robots.txt gövdesini ayrıştırır.

    Döner: (kurallar, sitemap listesi, crawl-delay, eşleşen user-agent).
    En spesifik eşleşen grup seçilir: tam token eşleşmesi > '*'.
    """
    groups: dict[str, list[RobotsRule]] = {}
    delays: dict[str, float] = {}
    sitemaps: list[str] = []
    current: list[str] = []
    # Ardışık User-agent satırları tek grubu paylaşır (REP).
    previous_was_agent = False

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower().lstrip("﻿")
        value = value.strip()

        if key == "user-agent":
            if not previous_was_agent:
                current = []
            current.append(value.lower())
            groups.setdefault(value.lower(), [])
            previous_was_agent = True
            continue
        previous_was_agent = False

        if key == "sitemap":
            sitemaps.append(value)
        elif key in ("disallow", "allow") and current:
            if key == "disallow" and value == "":
                continue  # boş Disallow = her şeye izin (kural üretme)
            for agent in current:
                groups[agent].append(RobotsRule(allow=(key == "allow"), pattern=value))
        elif key == "crawl-delay" and current:
            try:
                for agent in current:
                    delays[agent] = float(value.replace(",", "."))
            except ValueError:
                pass

    ua_token = user_agent.split("/", 1)[0].strip().lower()
    for candidate in (ua_token, "*"):
        if candidate in groups:
            return groups[candidate], sitemaps, delays.get(candidate), candidate
    return [], sitemaps, None, None


def _default_fetcher(timeout: float) -> Fetcher:
    """requests varsa onu, yoksa urllib kullanan çekici üretir."""

    def fetch(url: str) -> tuple[Optional[int], Optional[str]]:
        headers = {"User-Agent": DEFAULT_USER_AGENT}
        try:
            import requests  # type: ignore

            resp = requests.get(url, headers=headers, timeout=timeout)
            return resp.status_code, resp.text
        except ModuleNotFoundError:
            pass
        except Exception:
            return None, None
        import urllib.error
        import urllib.request

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                body = resp.read().decode("utf-8", errors="replace")
                return resp.status, body
        except urllib.error.HTTPError as exc:
            return exc.code, None
        except Exception:
            return None, None

    return fetch


class RobotsCache:
    """Origin başına robots.txt'i bir kez çeker, kararları önbelleğe alır."""

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, timeout: float = 15.0,
                 fetcher: Optional[Fetcher] = None, ignore: bool = False) -> None:
        self.user_agent = user_agent
        self.ignore = ignore
        self._fetch = fetcher or _default_fetcher(timeout)
        self._cache: dict[str, RobotsPolicy] = {}

    def policy_for(self, url: str) -> RobotsPolicy:
        origin = origin_of(url)
        if origin not in self._cache:
            self._cache[origin] = self._load(origin)
        return self._cache[origin]

    def _load(self, origin: str) -> RobotsPolicy:
        status, body = self._fetch(origin.rstrip("/") + "/robots.txt")
        if body is None or status != 200:
            return RobotsPolicy(origin=origin, status=status, fetched=False,
                                error=None if status else "baglanti hatasi")
        rules, sitemaps, delay, agent = parse_robots(body, self.user_agent)
        return RobotsPolicy(origin=origin, status=status, fetched=True, rules=rules,
                            sitemaps=sitemaps, crawl_delay=delay, matched_agent=agent)

    def allows(self, url: str) -> tuple[bool, str]:
        """(izin_var_mi, gerekce) — ignore=True ise izin verir ama gerekçede belirtir."""
        policy = self.policy_for(url)
        allowed = policy.allows(url)
        if allowed:
            return True, policy.reason(url)
        if self.ignore:
            return True, "robots.txt Disallow — --ignore-robots ile GECILDI"
        return False, policy.reason(url)

    def policies(self) -> dict[str, RobotsPolicy]:
        """Rapor için: çekilmiş tüm politikalar."""
        return dict(self._cache)
