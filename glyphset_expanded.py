"""Expanded glyph pool for sub-character profiling (see TODO.md items 2/3).

NARROW_GLYPHS (glyphset_narrow.py) plus nearly the full glyph coverage of
ciour/texgyrecursor-regular.otf (673 mapped codepoints), minus combining marks,
format characters, and the duplicate no-break space -- none of those can
stand alone in a single output cell. Every character below was confirmed
present in the font's cmap via fontTools before inclusion; ink-density
measurements (rendered pixel coverage per glyph) were used to rank light
vs. dark rather than guessing from Unicode category.

Box-drawing (U+2500 block), block elements (U+2580 block), and most
geometric shapes are still absent: TeX Gyre Cursor simply has no glyphs
in those ranges, so there was nothing to add there.

Finding worth flagging: this font has no filled/solid glyph. The darkest
characters available top out around 21% rendered ink coverage
(darkest 15, light-to-heaviest-first: ₩ ₦ ¶ № Ŋ Æ Ǽ Ħ Ḫ Ṃ Œ ğ β Ę ǽ) -- nowhere near a true
solid block. If the accuracy-comparison work (TODO item 3) ever needs a
genuinely "black" cell, this font cannot provide one; a block-elements-
capable font or the backlogged Braille dot-matrix mode would be the fix,
not more characters from this pool.
"""

from glyphset_narrow import NARROW_GLYPHS

# Latin-1 punctuation/symbols (30 chars)
_LATIN1_SYMBOLS = '¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿'

# Latin-1 accented letters (64 chars)
_LATIN1_LETTERS = 'ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ'

# Latin Extended-A (124 chars)
_LATIN_EXT_A = 'ĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥĦħĨĩĪīĬĭĮįİıĲĳĴĵĶķĹĺĻļĽľĿŀŁłŃńŅņŇňŊŋŌōŎŏŐőŒœŔŕŖŗŘřŚśŜŝŞşŠšŢţŤťŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽžſ'

# Latin Extended-B (51 chars)
_LATIN_EXT_B = 'ƎƒƠơƯưǍǎǏǐǑǒǓǔǗǘǙǚǛǜǝǦǧǪǫǰǴǵǺǻǼǽǾǿȀȁȄȅȈȉȌȍȐȑȔȕȘșȚțȷ'

# IPA Extensions (2 chars)
_IPA_EXTENSIONS = 'ɘə'

# Spacing Modifier Letters (10 chars)
_SPACING_MODIFIERS = 'ʾʿˆˇ˘˙˚˛˜˝'

# Greek and Coptic (54 chars)
_GREEK = 'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩαβγδεζηθικλμνξοπρςστυφχψωϑϕϖϱϵ'

# Latin Extended Additional (Vietnamese etc.) (133 chars)
_LATIN_EXT_ADD = 'ḌḍḎḏḤḥḦḧḪḫḮḯḶḷḸḹṂṃṄṅṆṇṘṙṚṛṜṝṢṣṬṭṮṯẀẁẂẃẄẅẒẓẗẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệỈỉỊịỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰựỲỳỴỵỶỷỸỹ'

# General Punctuation (28 chars)
_GENERAL_PUNCT = '‐‑–—‖‘’‚“”„†‡•…‰‱‹›※‽‿⁀⁄⁅⁆⁒⁔'

# Currency Symbols (8 chars)
_CURRENCY = '₡₤₦₩₫€₱₲'

# Letterlike Symbols (11 chars)
_LETTERLIKE = '℃ℓ№℗℘℞℠™Ω℧℮'

# Arrows (4 chars)
_ARROWS = '←↑→↓'

# Mathematical Operators (13 chars)
_MATH_OPERATORS = '∂∑−∓∗√∞∢≈≠≤≥⋆'

# Miscellaneous Technical (3 chars)
_MISC_TECHNICAL = '⌀〈〉'

# Misc Symbols/Dingbats (sparse in this font) (6 chars)
_MISC_SYMBOLS = '◊○◦♪⚭⚮'

# Supplemental Mathematical Operators (2 chars)
_SUPP_MATH = '⩽⩾'

# Supplemental Punctuation (2 chars)
_SUPP_PUNCT = '⸘⹀'

# Alphabetic Presentation Forms (ligatures) (3 chars)
_LIGATURES = 'ﬀﬁﬂ'

# Everything else (6 chars)
_OTHER = '฿␢␣⟦⟧🄯'

EXPANDED_GLYPHS = NARROW_GLYPHS + _LATIN1_SYMBOLS + _LATIN1_LETTERS + _LATIN_EXT_A + _LATIN_EXT_B + _IPA_EXTENSIONS + _SPACING_MODIFIERS + _GREEK + _LATIN_EXT_ADD + _GENERAL_PUNCT + _CURRENCY + _LETTERLIKE + _ARROWS + _MATH_OPERATORS + _MISC_TECHNICAL + _MISC_SYMBOLS + _SUPP_MATH + _SUPP_PUNCT + _LIGATURES + _OTHER
