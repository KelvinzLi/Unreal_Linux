"""Read-only inspection of uploaded BEDLAM sequences and their MRQ queue."""

import unreal


SEQUENCE_PATH = "/Game/Bedlam/LevelSequences/seq_000000_0"
QUEUE_PATH = "/Game/Bedlam/MovieRenderQueue/MRQ_Batch_00"


def prop(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return None


def text(value):
    if value is None:
        return ""
    try:
        return value.to_string()
    except Exception:
        return str(value)


def call(obj, name, *args):
    try:
        return getattr(obj, name)(*args)
    except Exception:
        return None


sequence = unreal.load_asset(SEQUENCE_PATH)
if sequence is None:
    raise RuntimeError("Could not load " + SEQUENCE_PATH)

movie_scene = sequence.get_movie_scene()
unreal.log_warning(
    "[BAKE_INSPECT] sequence={} display_rate={} tick_resolution={} "
    "playback_start={} playback_end={}".format(
        sequence.get_path_name(),
        text(sequence.get_display_rate()),
        text(sequence.get_tick_resolution()),
        sequence.get_playback_start(),
        sequence.get_playback_end(),
    )
)

for binding in sequence.get_bindings():
    binding_name = str(binding.get_display_name())
    if "Camera" not in binding_name and "camera" not in binding_name:
        continue
    unreal.log_warning(
        "[BAKE_INSPECT] binding={} id={}".format(
            binding_name,
            text(binding.get_id()),
        )
    )
    for track_index, track in enumerate(binding.get_tracks()):
        unreal.log_warning(
            "[BAKE_INSPECT] track={} class={} display={} property_path={}".format(
                track_index,
                track.get_class().get_name(),
                text(track.get_display_name()),
                text(prop(track, "property_path")),
            )
        )
        for section_index, section in enumerate(track.get_sections()):
            channels = section.get_all_channels()
            details = []
            for channel_index, channel in enumerate(channels):
                keys = channel.get_keys()
                default = call(channel, "get_default")
                first_time = call(keys[0], "get_time") if keys else None
                first_value = call(keys[0], "get_value") if keys else None
                last_time = call(keys[-1], "get_time") if keys else None
                last_value = call(keys[-1], "get_value") if keys else None
                details.append(
                    "{}:keys={},default={},first={}@{},last={}@{}".format(
                        channel_index,
                        len(keys),
                        text(default),
                        text(first_value),
                        text(first_time),
                        text(last_value),
                        text(last_time),
                    )
                )
            unreal.log_warning(
                "[BAKE_INSPECT] section={} active={} row={} "
                "range={}..{} channels=[{}]".format(
                    section_index,
                    call(section, "is_active"),
                    prop(section, "row_index"),
                    call(section, "get_start_frame"),
                    call(section, "get_end_frame"),
                    "; ".join(details),
                )
            )

queue = unreal.load_asset(QUEUE_PATH)
if queue is None:
    raise RuntimeError("Could not load " + QUEUE_PATH)

for index, job in enumerate(queue.get_jobs()):
    unreal.log_warning(
        "[BAKE_INSPECT] job={} name={} sequence={} map={}".format(
            index,
            text(prop(job, "job_name")),
            text(call(prop(job, "sequence"), "get_asset_path_string")),
            text(call(prop(job, "map"), "get_asset_path_string")),
        )
    )

unreal.log_warning("[BAKE_INSPECT] COMPLETE")
