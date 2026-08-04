# BEDLAM Linux rendering

Linux-specific camera diagnostics and rendering helpers for BEDLAM MRQ jobs.

See [LINUX_PIPELINE_RUNBOOK.md](LINUX_PIPELINE_RUNBOOK.md) for the complete
reproducible setup, plugin builds, rendering command, EXR fix, post-processing
changes, rollback paths, and validation checklist.

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

The runtime launcher preserves the production
`exr_image/{sequence_name}` and `exr_depth/{sequence_name}` output directories
and writes completion markers for full renders. Custom frame-range renders do
not write completion markers.

The Linux throw-simulation wrapper is `scripts/run_ue53_throw_simulation.sh`. It runs
the existing Syn4D simulation scripts unchanged inside a full offscreen UE 5.3
editor session. See the simulation section of `LINUX_PIPELINE_RUNBOOK.md`.
