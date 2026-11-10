"""Action glyphs: toolbars, menus, window controls, media controls, text formatting, lists and dialogs' small marks.
Names are the icon-naming-spec / GNOME names. Directional glyphs carry rtl=True and also ship a mirrored copy."""
import math

from glyphkit import *      # noqa: F401,F403
from glyphkit import add, S, F, FS, Part, arc, slash, with_badge, bang, dimmed, xf, head, cut_parts
from glyphs_status2 import arc_head, MOON, CLOUD, SHIELD
import ui_glyphs as U

OLD = U.GLYPHS


def old(i):
    return S(*OLD[i]["strokes"])


# ================================================================== go
_CH = {"previous": P((15, 5.5), (8.5, 12), (15, 18.5)), "next": P((9, 5.5), (15.5, 12), (9, 18.5)),
       "up": P((5.5, 15), (12, 8.5), (18.5, 15)), "down": P((5.5, 9), (12, 15.5), (18.5, 9))}
add("go-previous", "actions", S(_CH["previous"]), rtl=True)
add("go-next", "actions", S(_CH["next"]), rtl=True)
add("go-up", "actions", S(_CH["up"]))
add("go-down", "actions", S(_CH["down"]))
add("go-first", "actions", S(P((17, 5.5), (10.5, 12), (17, 18.5)), L(6, 5, 6, 19)), rtl=True)
add("go-last", "actions", S(P((7, 5.5), (13.5, 12), (7, 18.5)), L(18, 5, 18, 19)), rtl=True)
add("go-top", "actions", S(P((5.5, 18), (12, 11.5), (18.5, 18)), L(5, 5, 19, 5)))
add("go-bottom", "actions", S(P((5.5, 6), (12, 12.5), (18.5, 6)), L(5, 19, 19, 19)))
add("go-jump", "actions", S("M4 19v-3a5 5 0 0 1 5-5h11", head(20, 11, 1, 0, 4.5)), rtl=True)
add("go-home", "actions", old("home"), alias=("user-home",))
for _i, _n in (("left", "left"), ("right", "right"), ("up", "up"), ("down", "down")):
    add(f"arrow-{_i}", "actions", old(f"arrow-{_n}"))
add("pan-up", "ui", S(P((7, 14), (12, 9), (17, 14))))
add("pan-down", "ui", S(P((7, 10), (12, 15), (17, 10))))
add("pan-start", "ui", S(P((14, 7), (9, 12), (14, 17))), rtl=True)
add("pan-end", "ui", S(P((10, 7), (15, 12), (10, 17))), rtl=True)
add("chevrons-up-down", "ui", old("chevrons-up-down"))
add("external-link", "actions", S("M11 5H6.5A2.5 2.5 0 0 0 4 7.5v11A2.5 2.5 0 0 0 6.5 21h11a2.5 2.5 0 0 0 2.5-2.5V13", P((15, 3), (21, 3), (21, 9)), L(21, 3, 12, 12)))

# ================================================================== window and list controls
add("window-close", "ui", S(L(6, 6, 18, 18), L(18, 6, 6, 18)))
add("window-minimize", "ui", S(L(5, 18, 19, 18)), tags="anchored")      # the bar rests on the bottom edge, as in every window-control set
add("window-maximize", "ui", S(R(5, 5, 14, 14, 3)))
add("window-restore", "ui", S(RP([(9, 7), (9, 5), (19, 5), (19, 15), (17, 15)], 2.5), R(5, 9, 10, 10, 2.5)))
add("window-new", "ui", S(R(3, 4, 18, 16, 4), L(3, 8, 21, 8), L(12, 11.5, 12, 16.5), L(9.5, 14, 14.5, 14)))
add("tab-new", "actions", S(RP([(3, 20), (3, 4), (10, 4), (12, 8), (21, 8), (21, 20)], 3, closed=True), L(12, 11.5, 12, 16.5), L(9.5, 14, 14.5, 14)))
add("list-add", "actions", old("plus"))
add("list-remove", "actions", old("minus"))
add("list-remove-all", "actions", S(L(4, 7, 14, 7), L(4, 12, 14, 12), L(4, 17, 14, 17), L(16, 14, 21, 19), L(21, 14, 16, 19)))
add("open-menu", "actions", old("menu"))
add("view-more", "actions", F(*[disc(12, y, 1.7) for y in (5, 12, 19)]))
add("view-more-horizontal", "actions", F(*[disc(x, 12, 1.7) for x in (5, 12, 19)]))
add("folder-new", "actions", S(old("folder")[0].d, L(12, 11, 12, 17), L(9, 14, 15, 14)))
add("selection-mode", "actions", S(R(3, 3, 8, 8, 2), P((5.2, 7), (6.6, 8.4), (8.8, 5.6)), L(14, 7, 21, 7), R(3, 13, 8, 8, 2), L(14, 17, 21, 17)))

# ================================================================== document
_PAGE = RP([(5, 3), (14, 3), (19, 8), (19, 21), (5, 21)], 3, closed=True)
_FOLD = P((14, 3), (14, 8), (19, 8))
add("document-new", "actions", S(_PAGE, _FOLD, L(12, 12, 12, 18), L(9, 15, 15, 15)))
add("document-open", "actions", S("M3 19V5h6.500l2 3H19v3", "M3 19l2.600-8H22l-2.600 8Z"))
add("document-open-recent", "actions", S(arc(12, 12, 7.5, 100, 400), arc_head(12, 12, 7.5, 400, 3.5), P((12, 7), (12, 12), (15, 14))), alias=("folder-recent",))
_FLOP = [R(3, 3, 18, 18, 3), R(7, 3, 8, 6, 1), R(6, 14, 12, 7, 1.5)]
add("document-save", "actions", S(*_FLOP))
add("document-save-as", "actions", S(R(3, 3, 18, 18, 3), R(7, 3, 8, 6, 1), L(6, 14, 11, 14), L(6, 17, 9, 17), L(14, 20, 20, 14), L(20, 14, 21.5, 15.5)))
add("document-print-preview", "actions", S(_PAGE, _FOLD, C(11.5, 14.5, 2.8), L(13.6, 16.6, 16, 19)))
add("document-properties", "actions", S(_PAGE, _FOLD, L(8.5, 13, 15.5, 13), L(8.5, 17, 13, 17)))
add("document-send", "actions", old("send"), alias=("mail-send",), rtl=True)
add("document-edit", "actions", old("edit"))

# ================================================================== edit
add("edit-copy", "actions", old("copy"))
add("edit-cut", "actions", old("scissors"))
add("edit-paste", "actions", old("clipboard"))
add("edit-delete", "actions", S(L(3, 6, 21, 6), P((9, 6), (9, 3), (15, 3), (15, 6)), RP([(5, 6), (6, 21), (18, 21), (19, 6)], 2), L(10, 10, 10, 17), L(14, 10, 14, 17)), alias=("user-trash",))
add("edit-undo", "actions", old("undo"), rtl=True)
add("edit-redo", "actions", old("redo"), rtl=True)
add("edit-clear", "actions", S(Pc((21, 5), (8, 5), (2, 12), (8, 19), (21, 19)), L(11, 9, 16, 15), L(16, 9, 11, 15)), rtl=True)
add("edit-clear-all", "actions", S(L(4, 6, 20, 6), L(4, 11, 15, 11), L(4, 16, 11, 16), L(14, 14, 20, 20), L(20, 14, 14, 20)), rtl=True)
_LENS = [C(10, 10, 7), L(15, 15, 21, 21)]
add("edit-find", "actions", S(*_LENS), alias=("system-search",))
add("edit-find-replace", "actions", S(C(10, 10, 7), L(15, 15, 20, 20), L(7, 8, 13, 8), head(13, 8, 1, 0, 2.2), L(13, 12, 7, 12), head(7, 12, -1, 0, 2.2)))
add("edit-select-all", "actions", S(RP([(9, 4), (4, 4), (4, 9)], 2.5), RP([(15, 4), (20, 4), (20, 9)], 2.5), RP([(20, 15), (20, 20), (15, 20)], 2.5), RP([(9, 20), (4, 20), (4, 15)], 2.5)) + FS(R(9, 9, 6, 6, 1)))
add("action-unavailable", "actions", S(C(12, 12, 9), L(5.6, 5.6, 18.4, 18.4)))

# ================================================================== view
add("view-refresh", "actions", old("refresh"))
add("view-fullscreen", "actions", old("fullscreen"))
add("view-restore", "actions", old("minimize"))
add("view-grid", "actions", old("grid"))
add("view-app-grid", "actions", F(*[disc(x, y, 1.9) for y in (5, 12, 19) for x in (5, 12, 19)]))
add("view-list", "actions", S(L(4, 6, 20, 6), L(4, 12, 20, 12), L(4, 18, 20, 18)))
add("view-list-bullet", "actions", S(D(4.5, 7), L(9, 7, 20, 7), D(4.5, 12), L(9, 12, 20, 12), D(4.5, 17), L(9, 17, 20, 17)), rtl=True)
add("view-sort-ascending", "actions", S(L(4, 7, 10, 7), L(4, 12, 14, 12), L(4, 17, 18, 17), L(19, 5, 19, 19), P((16, 16), (19, 19), (22, 16))), rtl=True)
add("view-sort-descending", "actions", S(L(4, 7, 18, 7), L(4, 12, 14, 12), L(4, 17, 10, 17), L(19, 19, 19, 5), P((16, 8), (19, 5), (22, 8))), rtl=True)
add("view-pin", "actions", S("M9 4h6l-1 6 3 3v2H7v-2l3-3Z", L(12, 15, 12, 21)))
add("view-reveal", "actions", old("eye"))
add("view-conceal", "actions", slash(old("eye")))
add("view-paged", "actions", S(R(6, 3, 12, 18, 2.5)))
add("view-dual", "actions", S(R(2, 5, 9, 14, 2.5), R(13, 5, 9, 14, 2.5)))
add("view-continuous", "actions", S(R(5, 3, 14, 8, 2.5), R(5, 13, 14, 8, 2.5)))
add("view-mirror", "actions", S(R(3, 5, 7, 14, 2), R(14, 5, 7, 14, 2), L(12, 3, 12, 6), L(12, 10, 12, 14), L(12, 18, 12, 21)))
add("sidebar-show", "actions", S(R(3, 4, 18, 16, 4), L(10, 4, 10, 20)), rtl=True)
add("sidebar-show-right", "actions", S(R(3, 4, 18, 16, 4), L(14, 4, 14, 20)), rtl=True)
add("zoom-in", "actions", S(*_LENS, L(10, 7, 10, 13), L(7, 10, 13, 10)))
add("zoom-out", "actions", S(*_LENS, L(7, 10, 13, 10)))
add("zoom-fit-best", "actions", S(RP([(9, 4), (4, 4), (4, 9)], 2.5), RP([(15, 4), (20, 4), (20, 9)], 2.5), RP([(20, 15), (20, 20), (15, 20)], 2.5), RP([(9, 20), (4, 20), (4, 15)], 2.5), R(9, 9, 6, 6, 1.5)))
add("zoom-original", "actions", S(C(12, 12, 9), L(12, 8, 12, 16), P((10, 10), (12, 8))))

# ================================================================== bookmarks, favourites, places
add("bookmark-new", "actions", S(Pc((6, 4), (18, 4), (18, 21), (12, 16.5), (6, 21))), alias=("user-bookmarks",))
add("emblem-favorite", "emblems", FS(*OLD["heart"]["strokes"]))
add("mark-location", "actions", old("pin"), alias=("find-location",))
add("tag", "actions", old("tag"))
add("flag", "actions", old("flag"))
add("filter", "actions", old("filter"))
add("sliders", "actions", old("sliders"))
add("download", "actions", old("download"))
add("upload", "actions", old("upload"))
add("send-to", "actions", old("share"))
add("insert-link", "actions", old("link"))
add("insert-image", "actions", old("image"))
add("insert-object", "actions", S(R(3, 3, 18, 18, 4), L(12, 8, 12, 16), L(8, 12, 16, 12)))
add("insert-text", "actions", S(L(5, 5, 19, 5), L(12, 5, 12, 19), L(9, 19, 15, 19)))
add("color-select", "actions", S("M14 4l6 6", "M16.5 6.5L7 16l-2 4 4-2 9.5-9.5", "M17 3.5a2.100 2.100 0 0 1 3 3"))
add("font-select", "actions", S(P((3, 19), (8, 5), (13, 19)), L(5, 14, 11, 14), C(17, 16, 3), L(20, 13, 20, 19)))

# ================================================================== contacts, calls, mail
add("contact-new", "actions", S(C(10, 8, 4), "M3 20a7 7 0 0 1 14 0", L(19, 8, 19, 14), L(16, 11, 22, 11)))
add("address-book-new", "actions", S(R(4, 3, 14, 18, 3), C(11, 10, 2.5), "M7 17a4 4 0 0 1 8 0", L(21, 8, 21, 14)))
add("appointment-new", "actions", S(R(3, 5, 18, 16, 4), L(3, 9, 21, 9), L(8, 3, 8, 7), L(16, 3, 16, 7), L(12, 12.5, 12, 17.5), L(9.5, 15, 14.5, 15)))
add("chat-message-new", "actions", S(RP([(3, 4), (21, 4), (21, 17), (12.5, 17), (8, 21), (8, 17), (3, 17)], 4, closed=True), L(12, 7.5, 12, 12.5), L(9.5, 10, 14.5, 10)))
add("mail-message-new", "actions", S(R(3, 5, 18, 14, 4), L(12, 9, 12, 15), L(9, 12, 15, 12)))
_HS = "M6.500 4h3l1.500 4-2 1.500a10 10 0 0 0 5 5l1.500-2L20 14v3a2.500 2.500 0 0 1-2.500 2.500A15 15 0 0 1 4 6a2.500 2.500 0 0 1 2.500-2Z"
add("call-start", "actions", S(_HS))
add("call-stop", "actions", S(xf(_HS, 0.9, 0, 0.5, 135)))
add("mail-forward", "actions", S(P((15, 5), (21, 11), (15, 17)), "M21 11H10a7 7 0 0 0-7 7v1"), rtl=True)
add("mail-reply-sender", "actions", S(P((9, 5), (3, 11), (9, 17)), "M3 11h11a7 7 0 0 1 7 7v1"), rtl=True)
add("mail-reply-all", "actions", S(P((8, 5), (2.5, 10), (8, 15)), P((13, 5), (7.5, 10), (13, 15)), "M7.5 10h8.5a5 5 0 0 1 5 5v3"), rtl=True)
add("mail-mark-important", "actions", S(L(12, 4, 12, 14), D(12, 19.5)))
add("mail-mark-junk", "actions", S(Pc((8, 3), (16, 3), (21, 8), (21, 16), (16, 21), (8, 21), (3, 16), (3, 8)), L(12, 8, 12, 13), D(12, 16.2)))
add("mail-send-receive", "actions", S(L(4, 8, 19, 8), head(19, 8, 1, 0, 4.5), L(20, 16, 5, 16), head(5, 16, -1, 0, 4.5)), rtl=True)
add("camera-switch", "actions", S(R(3, 7, 18, 13, 3), P((8, 7), (9.5, 4), (14.5, 4), (16, 7)), arc(12, 13.5, 3.6, 205, 335), arc_head(12, 13.5, 3.6, 335, 2.6), arc(12, 13.5, 3.6, 25, 155), arc_head(12, 13.5, 3.6, 155, 2.6)))

# ================================================================== media
add("media-playback-start", "actions", FS(Pc((8, 5), (19, 12), (8, 19))), rtl=True)
add("media-playback-pause", "actions", FS(R(7, 5, 3, 14, 1), R(14, 5, 3, 14, 1)))
add("media-playback-stop", "actions", FS(R(6, 6, 12, 12, 2)))
add("media-record", "actions", FS(C(12, 12, 6)))
add("media-seek-backward", "actions", FS(Pc((10, 7), (4, 12), (10, 17)), Pc((20, 7), (14, 12), (20, 17))), rtl=True)
add("media-seek-forward", "actions", FS(Pc((4, 7), (10, 12), (4, 17)), Pc((14, 7), (20, 12), (14, 17))), rtl=True)
add("media-skip-backward", "actions", FS(Pc((19, 6), (9, 12), (19, 18))) + S(L(5, 5, 5, 19)), rtl=True)
add("media-skip-forward", "actions", FS(Pc((5, 6), (15, 12), (5, 18))) + S(L(19, 5, 19, 19)), rtl=True)
add("media-eject", "actions", FS(Pc((12, 5), (20, 15), (4, 15))) + S(L(5, 19, 19, 19)))
add("media-view-subtitles", "actions", S(R(3, 5, 18, 14, 3), L(7, 11, 10, 11), L(13, 11, 17, 11), L(7, 15, 12, 15)))

# ================================================================== objects
add("object-select", "actions", old("check"), alias=("emblem-ok",))
add("object-flip-horizontal", "actions", S(Pc((9, 6), (9, 18), (3, 18)), Pc((15, 6), (15, 18), (21, 18)), L(12, 3, 12, 6), L(12, 10.5, 12, 13.5), L(12, 18, 12, 21)))
add("object-flip-vertical", "actions", S(Pc((6, 9), (18, 9), (18, 3)), Pc((6, 15), (18, 15), (18, 21)), L(3, 12, 6, 12), L(10.5, 12, 13.5, 12), L(18, 12, 21, 12)))
add("object-rotate-left", "actions", S(arc(12, 11, 8.485, 220, -45), arc_head(12, 11, 8.485, -45, 3.5, cw=False)))
add("object-rotate-right", "actions", S(arc(12, 11, 8.485, -40, 225), arc_head(12, 11, 8.485, 225, 3.5)))


# ================================================================== text formatting
add("format-text-bold", "actions", S("M7 4h6.500a4 4 0 0 1 0 8H7", "M7 12h7.500a4 4 0 0 1 0 8H7", L(7, 4, 7, 20)))
add("format-text-italic", "actions", S(L(10, 4, 18, 4), L(6, 20, 14, 20), L(14, 4, 10, 20)))
add("format-text-underline", "actions", S("M7 4v7a5 5 0 0 0 10 0V4", L(5, 21, 19, 21)))
add("format-text-strikethrough", "actions", S("M17 7.500C16.500 5.800 14.800 4.500 12.500 4.500 9.800 4.500 8 5.900 8 8c0 4 9 3 9 8 0 2.200-2 3.500-5 3.500-2.500 0-4.300-1-5-2.500", L(4, 12, 20, 12)))
add("format-justify-left", "actions", S(L(4, 5, 20, 5), L(4, 10, 14, 10), L(4, 15, 20, 15), L(4, 20, 14, 20)), rtl=True)
add("format-justify-center", "actions", S(L(4, 5, 20, 5), L(7, 10, 17, 10), L(4, 15, 20, 15), L(7, 20, 17, 20)))
add("format-justify-right", "actions", S(L(4, 5, 20, 5), L(10, 10, 20, 10), L(4, 15, 20, 15), L(10, 20, 20, 20)), rtl=True)
add("format-justify-fill", "actions", S(L(4, 5, 20, 5), L(4, 10, 20, 10), L(4, 15, 20, 15), L(4, 20, 20, 20)))
add("format-indent-more", "actions", S(L(11, 6, 21, 6), L(11, 12, 21, 12), L(11, 18, 21, 18), P((3, 9), (6.500, 12), (3, 15))), rtl=True)
add("format-indent-less", "actions", S(L(11, 6, 21, 6), L(11, 12, 21, 12), L(11, 18, 21, 18), P((6.500, 9), (3, 12), (6.500, 15))), rtl=True)
add("process-stop", "actions", S(Pc((8, 3), (16, 3), (21, 8), (21, 16), (16, 21), (8, 21), (3, 16), (3, 8)), L(9, 9, 15, 15), L(15, 9, 9, 15)))
