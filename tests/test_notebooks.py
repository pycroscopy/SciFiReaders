"""Every markdown cell in the example notebooks must convert with pandoc,
otherwise the documentation build (nbsphinx) fails."""
import glob
import json
import shutil
import subprocess
import pytest

NOTEBOOKS = sorted(glob.glob('notebooks/**/*.ipynb', recursive=True))


@pytest.mark.skipif(shutil.which('pandoc') is None, reason='pandoc not installed')
@pytest.mark.parametrize('path', NOTEBOOKS)
def test_markdown_cells_convert(path):
    with open(path, encoding='utf-8') as f:
        nb = json.load(f)
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] != 'markdown':
            continue
        src = ''.join(cell['source'])
        result = subprocess.run(['pandoc', '--from', 'markdown', '--to', 'json'],
                                input=src.encode('utf-8'), capture_output=True)
        assert result.returncode == 0, (
            f'{path} cell {i}: pandoc failed\n{result.stderr.decode()}')