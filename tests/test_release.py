def test_release_check_blocks_private_files_and_values_without_echo(tmp_path):
    from sidam.release import check_paths
    (tmp_path / '.env').write_text('GMS_KEY=dummy-private-value', encoding='utf-8')
    (tmp_path / '.env.example').write_text('GMS_KEY=\nWIKI_CONTACT=\n', encoding='utf-8')
    (tmp_path / 'leak.txt').write_text('연락처 dummy-private-value', encoding='utf-8')
    errors = check_paths(tmp_path, ['.env', '.env.example', 'leak.txt'], private_values=['dummy-private-value'])
    assert any(e.startswith('.env:') for e in errors)
    assert any(e.startswith('leak.txt:') for e in errors)
    assert not any(e.startswith('.env.example:') for e in errors)
    assert all('dummy-private-value' not in e for e in errors)


def test_release_check_rejects_personal_template_and_local_artifacts(tmp_path):
    from sidam.release import check_paths
    (tmp_path / '.env.example').write_text('GMS_KEY=\nWIKI_CONTACT=someone@example.org\n', encoding='utf-8')
    assert check_paths(tmp_path, ['.env.example'])
    assert check_paths(tmp_path, ['.sidam/chroma.db', 'data/cache/a.html', 'tmp/log.txt'])


def test_gitignore_excludes_local_files_and_keeps_repro_inputs(tmp_path):
    import os
    import subprocess
    from pathlib import Path
    from sidam.repro import INPUT_FILES

    root = Path(__file__).resolve().parents[1]
    (tmp_path / '.gitignore').write_bytes((root / '.gitignore').read_bytes())
    empty_excludes = tmp_path / 'empty-excludes'
    empty_excludes.write_text('', encoding='utf-8')
    env = {**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull}
    subprocess.run(['git', 'init', '-q', str(tmp_path)], env=env, check=True)
    private = {
        '.env', '.env.local', '.env.production', 'nested/.env.local',
        '.streamlit/secrets.toml', '.venv/file.py', '.sidam/chroma/a.bin',
        'tmp/question.txt', 'data/cache/page.html', 'data/derived/notes.jsonl',
        'evaluation/runs/answers.json', 'private.pem', 'private.key', 'private.p12',
        'cache.sqlite', 'cache.sqlite3', 'cache.db', 'cache.sqlite-wal',
        'cache.sqlite3-shm', 'cache.db-journal',
    }
    shared = set(INPUT_FILES) | {
        'data/repro/manifest.json', 'data/repro/README.md',
        'sidam/ui.py', 'step7_skeleton.py', 'scripts/index_sidam.py',
        'scripts/verify_repro.py', 'docs/REPRODUCE.md',
        'submit/시담_제출본_20261023/README.md',
        'submit/시담_제출본_20261023/요구사항 정의서.docx',
    }
    result = subprocess.run(
        ['git', '-c', f'core.excludesFile={empty_excludes}',
         'check-ignore', '--no-index', '--stdin', '-z'],
        input='\0'.join(sorted(private | shared)) + '\0',
        cwd=tmp_path, env=env, encoding='utf-8', capture_output=True,
    )
    assert result.returncode in (0, 1), result.stderr
    ignored = set(result.stdout.split('\0')) - {''}
    assert not (ignored & shared), f'공유 입력이 제외됨: {sorted(ignored & shared)}'
    assert private <= ignored, f'개인 파일 제외 누락: {sorted(private - ignored)}'
