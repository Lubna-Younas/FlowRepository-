"""Regression coverage for upload readiness and the beginner run flow."""
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
import streamlit as st
from flowio import create_fcs
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'src/flowworkbench/app.py'


def upload(name, events):
    data = BytesIO()
    create_fcs(data, np.asarray(events, dtype='float32').ravel().tolist(),
               ['MarkerA', 'MarkerB'], metadata_dict={'cyt': 'SYNTHETIC_NOT_AN_INSTRUMENT'})
    data.name = name
    return data


def own_files_app():
    app = AppTest.from_file(str(APP))
    app.session_state['navigation'] = 'Analyze'
    app.session_state['input_mode'] = 'My FCS files'
    return app.run(timeout=30)


def test_empty_upload_explains_why_run_is_disabled():
    app = own_files_app()
    assert not app.exception
    assert app.button(key='run_analysis').label == 'Run analysis'
    assert app.button(key='run_analysis').disabled
    assert any('First upload your FCS files' in notice.value for notice in app.info)


def test_synthetic_upload_readiness_and_completed_run(monkeypatch):
    files = [upload('valid.fcs', np.random.default_rng(5).normal(100, 20, (60, 2))),
             upload('zero_events.fcs', np.empty((0, 2)))]
    # AppTest does not supply an upload setter; provide real in-memory FCS bytes
    # at that boundary and execute the actual inspection/analysis/report engine.
    monkeypatch.setattr(st, 'file_uploader', lambda label, *a, **kw: files if label == 'Select FCS files' else None)
    app = own_files_app()
    assert not app.exception
    assert app.button(key='run_analysis').disabled
    assert any('zero recorded events' in error.value for error in app.error)
    next(b for b in app.button if b.label == 'Use synthetic test settings').click().run(timeout=30)
    assert not app.exception
    assert app.multiselect(key='own_markers').value == ['MarkerA', 'MarkerB']
    assert app.selectbox(key='own_signal_state').value == 'synthetic'
    assert app.button(key='run_analysis').disabled  # Never silently skip the empty file.
    files.pop()
    app.run(timeout=30)
    assert not app.button(key='run_analysis').disabled
    app.selectbox(key='own_instrument').set_value('aurora').run(timeout=30)
    assert app.selectbox(key='own_signal_state').value == 'unknown'
    assert app.button(key='run_analysis').disabled
    next(b for b in app.button if b.label == 'Use synthetic test settings').click().run(timeout=30)
    app.button(key='run_analysis').click().run(timeout=60)
    assert not app.exception
    assert app.radio(key='navigation').value == 'Results'
    result = app.session_state['result']
    assert result['summary']['events'] == 60
    assert result['summary']['samples'] == 1
    assert result['config']['signal_state'] == 'synthetic'


def test_malformed_upload_keeps_visible_disabled_button(monkeypatch):
    bad = BytesIO(b'not an FCS file'); bad.name = 'broken.fcs'
    monkeypatch.setattr(st, 'file_uploader', lambda label, *a, **kw: [bad] if label == 'Select FCS files' else None)
    app = own_files_app()
    assert not app.exception
    assert app.error
    assert app.button(key='run_analysis').disabled
    assert any('Resolve the file errors' in warning.value for warning in app.warning)


def test_example_mode_still_has_its_own_ready_run_button():
    if not list((ROOT/'data/raw/flowkit/data/8_color_data_set/fcs_files').glob('*.fcs')):
        pytest.skip('Public example not downloaded')
    app = own_files_app()
    app.radio(key='input_mode').set_value('Example data').run(timeout=30)
    assert not app.exception
    assert app.button(key='run_analysis').label == 'Run example analysis'
    assert not app.button(key='run_analysis').disabled
    assert len(app.multiselect(key='demo_markers').value) == 3
