"""Print the active Unreal lighting and shadow state without modifying assets."""

import unreal


PREFIX = "[BEDLAM_LIGHTING]"


def value_text(value):
    try:
        return str(value)
    except Exception:
        return repr(value)


def print_properties(label, obj, names):
    unreal.log_warning(f"{PREFIX} {label}")
    if obj is None:
        unreal.log_warning(f"{PREFIX}   <component not found>")
        return

    for name in names:
        try:
            value = obj.get_editor_property(name)
        except Exception as exc:
            value = f"<unavailable: {exc}>"
        unreal.log_warning(f"{PREFIX}   {name}={value_text(value)}")


world = unreal.EditorLevelLibrary.get_editor_world()
actors = unreal.EditorLevelLibrary.get_all_level_actors()

unreal.log_warning(f"{PREFIX} world={world.get_path_name()}")

for actor in actors:
    if isinstance(actor, unreal.DirectionalLight):
        component = actor.get_component_by_class(
            unreal.DirectionalLightComponent
        )
        print_properties(
            f"DirectionalLight actor={actor.get_path_name()}",
            component,
            [
                "mobility",
                "intensity",
                "light_color",
                "use_temperature",
                "temperature",
                "source_angle",
                "shadow_bias",
                "shadow_slope_bias",
                "shadow_sharpen",
                "contact_shadow_length",
                "contact_shadow_length_in_ws",
                "dynamic_shadow_distance_movable_light",
                "dynamic_shadow_distance_stationary_light",
                "dynamic_shadow_cascades",
                "cascade_distribution_exponent",
                "cascade_transition_fraction",
                "shadow_distance_fadeout_fraction",
                "use_ray_traced_distance_field_shadows",
                "cast_shadows",
                "cast_dynamic_shadows",
                "cast_static_shadows",
                "affect_world",
                "atmosphere_sun_light",
                "atmosphere_sun_light_index",
            ],
        )

    if isinstance(actor, unreal.SkyLight):
        component = actor.get_component_by_class(unreal.SkyLightComponent)
        print_properties(
            f"SkyLight actor={actor.get_path_name()}",
            component,
            [
                "mobility",
                "intensity",
                "light_color",
                "source_type",
                "real_time_capture",
                "cubemap",
                "cubemap_resolution",
                "lower_hemisphere_is_solid_color",
                "lower_hemisphere_color",
                "cast_shadows",
                "cast_ray_traced_shadow",
                "affect_world",
            ],
        )

    if isinstance(actor, unreal.ExponentialHeightFog):
        component = actor.get_component_by_class(
            unreal.ExponentialHeightFogComponent
        )
        print_properties(
            f"ExponentialHeightFog actor={actor.get_path_name()}",
            component,
            [
                "fog_density",
                "fog_height_falloff",
                "fog_inscattering_color",
                "directional_inscattering_color",
                "volumetric_fog",
                "volumetric_fog_scattering_distribution",
                "volumetric_fog_albedo",
                "volumetric_fog_emissive",
                "volumetric_fog_extinction_scale",
                "volumetric_fog_view_distance",
            ],
        )

    if isinstance(actor, unreal.PostProcessVolume):
        print_properties(
            f"PostProcessVolume actor={actor.get_path_name()}",
            actor,
            [
                "enabled",
                "unbound",
                "priority",
                "blend_radius",
                "blend_weight",
            ],
        )
        print_properties(
            "PostProcess settings",
            actor.get_editor_property("settings"),
            [
                "auto_exposure_method",
                "auto_exposure_bias",
                "auto_exposure_min_brightness",
                "auto_exposure_max_brightness",
                "auto_exposure_min_ev100",
                "auto_exposure_max_ev100",
                "ambient_occlusion_intensity",
                "ambient_occlusion_radius",
            ],
        )


unreal.log_warning(f"{PREFIX} Console-variable queries follow")
for command in [
    "r.Shadow.Virtual.Enable",
    "r.DistanceFieldShadowing",
    "r.DFFullResolution",
    "r.DFShadowQuality",
    "r.ContactShadows",
    "r.ShadowQuality",
    "r.Shadow.MaxResolution",
    "r.Shadow.MaxCSMResolution",
    "r.Shadow.CSM.MaxCascades",
    "r.Shadow.DistanceScale",
    "r.Shadow.CSM.TransitionScale",
    "r.Shadow.FilterMethod",
    "r.Shadow.TexelsPerPixel",
    "r.Shadow.RadiusThreshold",
    "r.AntiAliasingMethod",
    "r.SSGI.Quality",
    "r.AmbientOcclusionLevels",
    "r.EyeAdaptationQuality",
]:
    unreal.SystemLibrary.execute_console_command(world, command)

unreal.log_warning(f"{PREFIX} done")
