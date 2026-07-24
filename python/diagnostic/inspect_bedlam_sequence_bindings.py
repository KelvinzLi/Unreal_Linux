"""Read-only dump of BEDLAM MRQ jobs and all sequence bindings/tracks."""

import unreal


QUEUE_PATH = "/Game/Bedlam/MovieRenderQueue/MRQ_Batch_00"


def safe(obj, method, *args):
    try:
        return getattr(obj, method)(*args)
    except Exception as exc:
        return "<error:{}>".format(exc)


def prop(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return None


def path_from_soft(value):
    result = safe(value, "get_asset_path_string")
    if isinstance(result, str) and not result.startswith("<error:"):
        return result
    return str(value)


queue = unreal.load_asset(QUEUE_PATH)
if queue is None:
    raise RuntimeError("Could not load {}".format(QUEUE_PATH))

sequence_paths = ["/Game/Bedlam/LevelSequences/seq_000000_0"]
for job_index, job in enumerate(queue.get_jobs()):
    sequence_path = path_from_soft(prop(job, "sequence"))
    unreal.log_warning(
        "[SEQ_DUMP] JOB index={} name={} sequence={} map={} enabled={}".format(
            job_index,
            prop(job, "job_name"),
            sequence_path,
            path_from_soft(prop(job, "map")),
            prop(job, "enabled"),
        )
    )
for sequence_path in dict.fromkeys(sequence_paths):
    sequence = unreal.load_asset(sequence_path)
    if sequence is None:
        unreal.log_error("[SEQ_DUMP] LOAD_FAILED {}".format(sequence_path))
        continue

    unreal.log_warning(
        "[SEQ_DUMP] SEQUENCE path={} bindings={} playback={}..{} "
        "display_rate={} tick_resolution={}".format(
            sequence.get_path_name(),
            len(sequence.get_bindings()),
            sequence.get_playback_start(),
            sequence.get_playback_end(),
            sequence.get_display_rate(),
            sequence.get_tick_resolution(),
        )
    )

    for binding_index, binding in enumerate(sequence.get_bindings()):
        tracks = binding.get_tracks()
        unreal.log_warning(
            "[SEQ_DUMP] BINDING index={} name={} id={} tracks={} "
            "possessable={} spawnable={}".format(
                binding_index,
                binding.get_display_name(),
                binding.get_id(),
                len(tracks),
                safe(sequence, "find_possessable", binding.get_id()),
                safe(sequence, "find_spawnable", binding.get_id()),
            )
        )
        for track_index, track in enumerate(tracks):
            sections = track.get_sections()
            unreal.log_warning(
                "[SEQ_DUMP] TRACK binding={} index={} class={} name={} "
                "property={} sections={}".format(
                    binding.get_display_name(),
                    track_index,
                    track.get_class().get_name(),
                    safe(track, "get_display_name"),
                    prop(track, "property_path"),
                    len(sections),
                )
            )
            for section_index, section in enumerate(sections):
                channels = safe(section, "get_all_channels")
                unreal.log_warning(
                    "[SEQ_DUMP] SECTION binding={} track={} index={} "
                    "class={} active={} range={}..{} channels={}".format(
                        binding.get_display_name(),
                        track.get_class().get_name(),
                        section_index,
                        section.get_class().get_name(),
                        safe(section, "is_active"),
                        safe(section, "get_start_frame"),
                        safe(section, "get_end_frame"),
                        len(channels) if not isinstance(channels, str) else channels,
                    )
                )
                if not isinstance(channels, str):
                    for channel_index, channel in enumerate(channels):
                        keys = safe(channel, "get_keys")
                        if isinstance(keys, str):
                            unreal.log_warning(
                                "[SEQ_DUMP] CHANNEL binding={} track={} index={} error={}".format(
                                    binding.get_display_name(),
                                    track.get_class().get_name(),
                                    channel_index,
                                    keys,
                                )
                            )
                            continue
                        values = [safe(key, "get_value") for key in keys]
                        times = [safe(key, "get_time") for key in keys]
                        unreal.log_warning(
                            "[SEQ_DUMP] CHANNEL binding={} track={} index={} "
                            "keys={} default={} first={}@{} last={}@{} "
                            "min={} max={}".format(
                                binding.get_display_name(),
                                track.get_class().get_name(),
                                channel_index,
                                len(keys),
                                safe(channel, "get_default"),
                                values[0] if values else None,
                                times[0] if times else None,
                                values[-1] if values else None,
                                times[-1] if times else None,
                                min(values) if values else None,
                                max(values) if values else None,
                            )
                        )

    for track_index, track in enumerate(sequence.get_master_tracks()):
        unreal.log_warning(
            "[SEQ_DUMP] MASTER_TRACK index={} class={} name={} sections={}".format(
                track_index,
                track.get_class().get_name(),
                safe(track, "get_display_name"),
                len(track.get_sections()),
            )
        )

unreal.log_warning("[SEQ_DUMP] COMPLETE")
