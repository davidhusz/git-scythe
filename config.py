import subprocess


def get(key, default):
    try:
        value = subprocess.run(
            ['git', 'config', '--get', 'scythe.' + key],
            capture_output = True,
            text = True,
            check = True
        ).stdout.strip()
    except subprocess.CalledProcessError:
        subprocess.run(
            ['git', 'config', '--add', 'scythe.' + key, default],
            capture_output = True,
            check = True
        )
        value = default

    return value
