"""완성된 확장 빌드를 개인 설치용 ZIP으로 묶고 내용과 해시를 검사한다."""
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'extension/dist'


def main():
    manifest = json.loads((BUILD / 'manifest.json').read_text(encoding='utf-8'))
    version = manifest['version']
    if manifest['manifest_version'] != 3 or not re.fullmatch(r'\d+(\.\d+){1,3}', version):
        raise ValueError('확장 버전 또는 manifest가 올바르지 않습니다.')
    required = ['manifest.json', manifest['background']['service_worker'],
                manifest['side_panel']['default_path'], 'editor.html', 'shared.js', 'THIRD_PARTY_NOTICES.txt']
    required += [script for entry in manifest['content_scripts'] for script in entry['js']]
    for name in required:
        if not (BUILD / name).is_file():
            raise ValueError(f'빌드 파일 누락: {name}')
    output = ROOT / 'release' / f'clipman-extension-{version}-personal.zip'
    output.parent.mkdir(exist_ok=True)
    temporary = output.with_suffix('.zip.tmp')
    files = sorted(p for p in BUILD.rglob('*') if p.is_file())
    with ZipFile(temporary, 'w', compression=ZIP_DEFLATED) as bundle:
        for path in files:
            if not path.resolve().is_relative_to(BUILD.resolve()):
                raise ValueError('빌드 폴더 밖의 파일은 포함하지 않습니다.')
            info = ZipInfo(path.relative_to(BUILD).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            bundle.writestr(info, path.read_bytes())
    with ZipFile(temporary) as bundle:
        assert bundle.testzip() is None
        assert sorted(bundle.namelist()) == sorted(p.relative_to(BUILD).as_posix() for p in files)
        for path in files:
            assert bundle.read(path.relative_to(BUILD).as_posix()) == path.read_bytes()
    temporary.replace(output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(f'{digest}  {output.name}\n', encoding='utf-8')
    print(json.dumps({'artifact': str(output), 'version': version, 'files': len(files),
                      'bytes': output.stat().st_size, 'sha256': digest}))


if __name__ == '__main__':
    main()
