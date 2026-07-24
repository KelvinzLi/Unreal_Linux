# BEDLAM Linux rendering

Linux-specific camera diagnostics and rendering helpers for BEDLAM MRQ jobs.

The confirmed camera stabilization settings are:

```text
tick.AllowAsyncTickDispatch=0
tick.AllowConcurrentTickQueue=0
```

The persistent `BE_CineCameraActor_Blueprint` must track
`BE_CameraTarget`. In each MRQ PIE world, enforce this tick dependency:

```python
camera.add_tick_prerequisite_actor(controller)
```

This means the `PlayerController` ticks before the camera.

The current runtime probe under `python/diagnostic/` writes both MRQ jobs into
one flat directory. It is
intended for camera validation, not final BEDLAM dataset production. A
production launcher must preserve the queue's `exr_image/{sequence_name}` and
`exr_depth/{sequence_name}` output directories and completion markers.
