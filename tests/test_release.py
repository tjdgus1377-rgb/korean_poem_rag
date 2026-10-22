def test_release_check_blocks_private_files_and_values_without_echo(tmp_path):
    from sidam.release import check_paths
    (tmp_path / '.env').write_text('GMS_KEY=dummy-private-value')
    (tmp_path / '.env.example').write_text('GMS_KEY=\nWIKI_CONTACT=\n')
    (tmp_path / 'leak.txt').write_text('연락처 dummy-private-value')
    errors = check_paths(tmp_path, ['.env', '.env.example', 'leak.txt'], private_values=['dummy-private-value'])
    assert any(e.startswith('.env:') for e in errors)
    assert any(e.startswith('leak.txt:') for e in errors)
    assert not any(e.startswith('.env.example:') for e in errors)
    assert all('dummy-private-value' not in e for e in errors)


def test_release_check_rejects_personal_template_and_local_artifacts(tmp_path):
    from sidam.release import check_paths
    (tmp_path / '.env.example').write_text('GMS_KEY=\nWIKI_CONTACT=someone@example.org\n')
    assert check_paths(tmp_path, ['.env.example'])
    assert check_paths(tmp_path, ['.sidam/chroma.db', 'data/cache/a.html', 'tmp/log.txt'])
