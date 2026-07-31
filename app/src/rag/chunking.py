"""Kampanya metnini gömme (embedding) parçalarına böler.

İlgili: CLAUDE.md §8 (src/rag: chunk → embed → retrieve → generate)
        ../preprocessing/clean.py (TR-duyarlı cümle segmentasyonu)

Sıfır üçüncü parti bağımlılık: bölme, mevcut `split_sentences()` üzerine kurulu.

## Neden cümle sınırında bölünür

Kampanya metinlerinde sayısal koşullar cümleye bağlıdır: "İlk 6 ay %0 kâr payı"
cümlenin ortasından kesilirse parça "%0" içerir ama "ilk 6 ay" koşulunu
kaybeder — retriever alakalı görünen ama YANLIŞ bir pasaj döndürür. Bu,
CLAUDE.md §6'daki "zor anlama" vakalarının aynen kaybedilmesi demektir.

Cümle bir parçaya sığmayacak kadar uzunsa (nadiren; tablo dökümü olmuş HTML)
sert karakter kesimine düşülür — sessizce atılmaz.
"""

from __future__ import annotations

from ..preprocessing.clean import normalize_whitespace, split_sentences

# bge-m3 8192 token'a kadar alır; parçaları küçük tutmak retrieval hassasiyetini
# artırır (uzun parçada tek alakalı cümle gürültüde kaybolur).
DEFAULT_CHUNK_CHARS = 800
# Örtüşme: cümle sınırında bölünen bir koşulun iki parçada da görünmesi için.
DEFAULT_OVERLAP_CHARS = 120


def chunk_text(text: str, max_chars: int = DEFAULT_CHUNK_CHARS,
               overlap_chars: int = DEFAULT_OVERLAP_CHARS) -> list[str]:
    """Metni en fazla `max_chars` uzunluğunda, cümle sınırlı parçalara böler.

    Boş/boşluk metin için boş liste döner (gömülecek bir şey yok).
    """
    if max_chars <= 0:
        raise ValueError("max_chars pozitif olmalı")
    if not 0 <= overlap_chars < max_chars:
        raise ValueError("overlap_chars [0, max_chars) aralığında olmalı")

    text = normalize_whitespace(text)
    if not text:
        return []

    parts: list[str] = []
    current = ""
    for sentence in split_sentences(text) or [text]:
        for piece in _split_long(sentence, max_chars):
            if not current:
                current = piece
            elif len(current) + 1 + len(piece) <= max_chars:
                current = f"{current} {piece}"
            else:
                parts.append(current)
                current = _with_overlap(current, piece, overlap_chars, max_chars)
    if current:
        parts.append(current)
    return parts


def _with_overlap(previous: str, piece: str, overlap_chars: int,
                  max_chars: int) -> str:
    """Yeni parçayı önceki parçanın son `overlap_chars` karakteriyle başlatır."""
    if overlap_chars <= 0:
        return piece
    tail = previous[-overlap_chars:].lstrip()
    if not tail or len(tail) + 1 + len(piece) > max_chars:
        return piece
    return f"{tail} {piece}"


def _split_long(sentence: str, max_chars: int) -> list[str]:
    """`max_chars`'tan uzun tek cümleyi sert keser (kaybetmemek için)."""
    if len(sentence) <= max_chars:
        return [sentence]
    return [sentence[i:i + max_chars] for i in range(0, len(sentence), max_chars)]
