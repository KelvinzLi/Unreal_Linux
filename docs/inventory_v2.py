"""Read-only V2 directory inventory; writes only the explicitly requested report.

Counts sequence-level artifacts, reads camera CSVs and small JSON/header samples.
Does not scan every image, load tensor payloads, or modify dataset contents.
"""
import argparse
import collections
import csv
import datetime
import json
from pathlib import Path
import struct


def names(path, suffix):
    return sorted(p.name for p in path.iterdir() if p.name.endswith(suffix)) if path.is_dir() else []


def header(path):
    with path.open('rb') as f:
        length = struct.unpack('<Q', f.read(8))[0]
        if length > 10_000_000:
            raise ValueError(f'Unexpected header length: {path}')
        return json.loads(f.read(length))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    report = {'root': str(root), 'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'scope': 'Sequence artifact presence and camera row counts, not full payload integrity or geometric quality.',
              'top_level': {}, 'splits': {}}
    for p in sorted(root.iterdir()):
        if p.is_dir():
            entries = sorted(p.iterdir())
            report['top_level'][p.name] = {'entries': [x.name for x in entries]}
            archives = [x for x in entries if x.name.endswith('.tar.zst')]
            if archives:
                report['top_level'][p.name]['archive_bytes'] = sum(x.stat().st_size for x in archives)
    for split in ('mixed', 'mixed_no_sim_corrected', 'nvs_outpaint'):
        scenes = {}
        for scene in sorted((root/split).iterdir()):
            if not scene.is_dir() or not (scene/'be_seq.csv').is_file():
                continue
            print(f'[inventory] {split}/{scene.name}', flush=True)
            sets = {}
            for key, folder, suffix in (
                ('mp4', scene/'mp4', '.mp4'),
                ('tracking', scene/'tracking_safetensors', '.safetensors'),
                ('tracking_index', scene/'tracking_safetensors', '_index.json'),
                ('tracking_log', scene/'tracking_safetensors', '_log.json'),
                ('attachments', root/(split+'_attachments')/scene.name/'tracking_attachments_safetensors', '.safetensors'),
                ('attachment_index', root/(split+'_attachments')/scene.name/'tracking_attachments_safetensors', '_index.json'),
                ('attachment_log', root/(split+'_attachments')/scene.name/'tracking_attachments_safetensors', '_log.json'),
                ('rgb_camera', scene/'ground_truth/meta_exr_csv', '_camera.csv'),
                ('depth_camera', scene/'ground_truth/meta_exr_depth_csv', '_camera.csv'),
            ):
                sets[key] = {n[:-len(suffix)] for n in names(folder, suffix)}
            counts = {k: len(v) for k, v in sets.items()}
            differences = {k: sorted(sets['mp4'] ^ v) for k, v in sets.items() if v != sets['mp4']}
            frames = {}
            for seq in sorted(sets['rgb_camera']):
                with (scene/'ground_truth/meta_exr_csv'/f'{seq}_camera.csv').open() as f:
                    frames[seq] = sum(1 for _ in csv.DictReader(f))
            info = {'counts': counts, 'sequence_set_differences_from_mp4': differences,
                    'camera_frame_counts': frames,
                    'frame_count_histogram': dict(sorted(collections.Counter(frames.values()).items())),
                    'files': sorted(p.name for p in scene.iterdir())}
            cameras = json.loads((scene/'be_camera_animations.json').read_text())
            info['camera_global_info'] = cameras.get('info')
            info['camera_first_sequence'] = next((v for k,v in cameras.items() if k != 'info'), None)
            seq = sorted(sets['mp4'])[0]
            for key, path in [('tracking_sample', scene/'tracking_safetensors'/f'{seq}.safetensors'),
                              ('attachment_sample', root/(split+'_attachments')/scene.name/'tracking_attachments_safetensors'/f'{seq}.safetensors')]:
                if path.exists():
                    info[key] = {'path': str(path), 'bytes': path.stat().st_size, 'header': header(path)}
            samples = {}
            for rel in [f'png/{seq}', f'exr_layers/depth/{seq}', f'exr_layers/masks/{seq}', f'mp4/{seq}.mp4']:
                p = scene/rel
                samples[rel] = {'symlink': p.is_symlink(), 'resolved': str(p.resolve()), 'exists': p.exists()}
                if p.is_dir():
                    entries = sorted(p.iterdir())
                    samples[rel].update(count=len(entries), first_names=[x.name for x in entries[:6]])
            info['samples'] = samples
            scenes[scene.name] = info
        report['splits'][split] = scenes
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    for split, scenes in report['splits'].items():
        print(split, len(scenes), dict(sum((collections.Counter(s['counts']) for s in scenes.values()), collections.Counter())), flush=True)


if __name__ == '__main__':
    main()
