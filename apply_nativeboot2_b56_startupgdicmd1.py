#!/usr/bin/env python3
"""NATIVEBOOT2 B56 STARTUPGDICMD1.

Diagnostic-only follow-up to B55 DEVICE1.

B55 proves that the one-shot Startup server-redraw replay changes the display
from the stale Nokia splash to a stable white surface.  B55 logged one stored
segment, but its "drawable_segments" counter only means segment.type_ is not
PENDING_REDRAW; it does not prove that the segment contains a pixel-writing GDI
command.

B56 therefore inspects the exact stored GDI command stream replayed for the
physically-visible Startup 0x100058F4 canvas.  It records segment type/region,
command opcode, gdi_store_command_draws_pixels(), and bounded details for the
common draw/clip commands.

No redraw/present/focus/z-order/visibility/activation/clear behavior changes.
"""

from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B56-STARTUPGDICMD1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b56_startupgdicmd1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    path = up / "src/emu/services/src/window/classes/winuser.cpp"
    if not path.is_file():
        fail(f"missing source: {path}")

    text = path.read_text(encoding="utf-8")

    if "[NBOOT2][STARTUP_REPLAY_CANVAS]" not in text:
        fail("missing predecessor marker: [NBOOT2][STARTUP_REPLAY_CANVAS]")

    if "[NBOOT2][STARTUP_GDI_SEGMENT]" in text:
        if "[NBOOT2][STARTUP_GDI_CMD]" in text and "[NBOOT2][STARTUP_GDI_DETAIL]" in text:
            print(MARK + ": already applied")
            return
        fail("partial B56 patch detected")

    anchor = '''                LOG_WARN(SERVICE_WINDOW,
                    "[NBOOT2][STARTUP_REPLAY_CANVAS] group_id={} group_handle=0x{:08X} group_name={} canvas_handle=0x{:08X} abs=[{},{},{},{}] visible_region_empty={} segments={} drawable_segments={} background_region_empty={} clear_color_enable={} action=SERVER_SEGMENT_REPLAY behavior=CONTROLLED_EXPERIMENT",
'''

    if text.count(anchor) != 1:
        fail(f"expected one B55 canvas marker anchor, found {text.count(anchor)}")

    inject = r'''                std::size_t b56_total_commands = 0;
                std::size_t b56_pixel_commands = 0;

                for (std::size_t b56_seg_i = 0; b56_seg_i < segments.size(); b56_seg_i++) {
                    const gdi_store_command_segment &b56_seg = *segments[b56_seg_i];
                    std::size_t b56_seg_pixel_commands = 0;

                    for (std::size_t b56_cmd_i = 0; b56_cmd_i < b56_seg.commands_.size(); b56_cmd_i++) {
                        const gdi_store_command &b56_cmd = b56_seg.commands_[b56_cmd_i];
                        const bool b56_draws_pixels = gdi_store_command_draws_pixels(b56_cmd.opcode_);

                        b56_total_commands++;
                        if (b56_draws_pixels) {
                            b56_pixel_commands++;
                            b56_seg_pixel_commands++;
                        }

                        LOG_WARN(SERVICE_WINDOW,
                            "[NBOOT2][STARTUP_GDI_CMD] segment={} command={} segment_type={} opcode={} draws_pixels={} behavior=OBSERVE_ONLY",
                            b56_seg_i,
                            b56_cmd_i,
                            static_cast<std::uint32_t>(b56_seg.type_),
                            static_cast<std::uint32_t>(b56_cmd.opcode_),
                            b56_draws_pixels ? 1 : 0);

                        if (b56_cmd.opcode_ == gdi_store_command_draw_rect) {
                            const gdi_store_command_draw_rect_data &b56_d =
                                b56_cmd.get_data_struct_const<gdi_store_command_draw_rect_data>();
                            LOG_WARN(SERVICE_WINDOW,
                                "[NBOOT2][STARTUP_GDI_DETAIL] segment={} command={} kind=DRAW_RECT rect=[{},{},{},{}] rgba=[{},{},{},{}] behavior=OBSERVE_ONLY",
                                b56_seg_i, b56_cmd_i,
                                b56_d.rect_.top.x, b56_d.rect_.top.y,
                                b56_d.rect_.size.x, b56_d.rect_.size.y,
                                b56_d.color_.x, b56_d.color_.y,
                                b56_d.color_.z, b56_d.color_.w);
                        } else if (b56_cmd.opcode_ == gdi_store_command_draw_bitmap) {
                            const gdi_store_command_draw_bitmap_data &b56_d =
                                b56_cmd.get_data_struct_const<gdi_store_command_draw_bitmap_data>();
                            LOG_WARN(SERVICE_WINDOW,
                                "[NBOOT2][STARTUP_GDI_DETAIL] segment={} command={} kind=DRAW_BITMAP dest=[{},{},{},{}] source=[{},{},{},{}] flags=0x{:08X} main_drv=0x{:016X} mask_drv=0x{:016X} behavior=OBSERVE_ONLY",
                                b56_seg_i, b56_cmd_i,
                                b56_d.dest_rect_.top.x, b56_d.dest_rect_.top.y,
                                b56_d.dest_rect_.size.x, b56_d.dest_rect_.size.y,
                                b56_d.source_rect_.top.x, b56_d.source_rect_.top.y,
                                b56_d.source_rect_.size.x, b56_d.source_rect_.size.y,
                                b56_d.gdi_flags_,
                                static_cast<std::uint64_t>(b56_d.main_drv_),
                                static_cast<std::uint64_t>(b56_d.mask_drv_));
                        } else if (b56_cmd.opcode_ == gdi_store_command_draw_text) {
                            const gdi_store_command_draw_text_data &b56_d =
                                b56_cmd.get_data_struct_const<gdi_store_command_draw_text_data>();
                            LOG_WARN(SERVICE_WINDOW,
                                "[NBOOT2][STARTUP_GDI_DETAIL] segment={} command={} kind=DRAW_TEXT box=[{},{},{},{}] rgba=[{},{},{},{}] alignment={} behavior=OBSERVE_ONLY",
                                b56_seg_i, b56_cmd_i,
                                b56_d.text_box_.top.x, b56_d.text_box_.top.y,
                                b56_d.text_box_.size.x, b56_d.text_box_.size.y,
                                b56_d.color_.x, b56_d.color_.y,
                                b56_d.color_.z, b56_d.color_.w,
                                b56_d.alignment_);
                        } else if (b56_cmd.opcode_ == gdi_store_command_set_clip_rect_single) {
                            const gdi_store_command_set_clip_rect_single_data &b56_d =
                                b56_cmd.get_data_struct_const<gdi_store_command_set_clip_rect_single_data>();
                            LOG_WARN(SERVICE_WINDOW,
                                "[NBOOT2][STARTUP_GDI_DETAIL] segment={} command={} kind=CLIP_SINGLE rect=[{},{},{},{}] behavior=OBSERVE_ONLY",
                                b56_seg_i, b56_cmd_i,
                                b56_d.clipping_rect_.top.x, b56_d.clipping_rect_.top.y,
                                b56_d.clipping_rect_.size.x, b56_d.clipping_rect_.size.y);
                        } else if (b56_cmd.opcode_ == gdi_store_command_update_texture) {
                            const gdi_store_command_update_texture_data &b56_d =
                                b56_cmd.get_data_struct_const<gdi_store_command_update_texture_data>();
                            LOG_WARN(SERVICE_WINDOW,
                                "[NBOOT2][STARTUP_GDI_DETAIL] segment={} command={} kind=UPDATE_TEXTURE handle=0x{:016X} destroy_handle=0x{:016X} dim={}x{} bytes={} pixel_per_line={} behavior=OBSERVE_ONLY",
                                b56_seg_i, b56_cmd_i,
                                static_cast<std::uint64_t>(b56_d.handle_),
                                static_cast<std::uint64_t>(b56_d.destroy_handle_),
                                b56_d.dim_.x, b56_d.dim_.y,
                                b56_d.texture_size_, b56_d.pixel_per_line_);
                        }
                    }

                    LOG_WARN(SERVICE_WINDOW,
                        "[NBOOT2][STARTUP_GDI_SEGMENT] segment={} type={} region_rects={} commands={} pixel_commands={} creation_date={} behavior=OBSERVE_ONLY",
                        b56_seg_i,
                        static_cast<std::uint32_t>(b56_seg.type_),
                        b56_seg.region_.rects_.size(),
                        b56_seg.commands_.size(),
                        b56_seg_pixel_commands,
                        b56_seg.creation_date_);
                }

                LOG_WARN(SERVICE_WINDOW,
                    "[NBOOT2][STARTUP_GDI_SEGMENT] summary=1 segments={} commands={} pixel_commands={} behavior=OBSERVE_ONLY",
                    segments.size(), b56_total_commands, b56_pixel_commands);

'''

    text = text.replace(anchor, inject + anchor, 1)

    if text.count("[NBOOT2][STARTUP_GDI_SEGMENT]") != 2:
        fail("segment marker count mismatch")
    if text.count("[NBOOT2][STARTUP_GDI_CMD]") != 1:
        fail("command marker source count mismatch")
    if text.count("[NBOOT2][STARTUP_GDI_DETAIL]") != 5:
        fail("detail marker source count mismatch")
    if "flags_ |= FLAG_SERVER_REDRAW_PENDING" in inject:
        fail("B56 must not mutate redraw flags")

    path.write_text(text, encoding="utf-8")

    print(MARK + ": applied")
    print("scope=DIAGNOSTIC_ONLY")
    print("target=STARTUP_STORED_GDI_COMMAND_STREAM")
    print("behavior_change=NONE")
    print("B55_STARTUP_REPLAY=PRESERVED")

if __name__ == "__main__":
    main()
