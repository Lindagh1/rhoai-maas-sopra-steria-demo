from pathlib import Path
from types import SimpleNamespace as Obj
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'ventes/scripts'))
from preparer import digest, ensure_pipeline

class PipelineReuseTests(unittest.TestCase):
    def run_existing(self, run_state):
        with tempfile.TemporaryDirectory() as directory:
            package=Path(directory)/'pipeline.yaml'
            package.write_bytes(b'package-test')
            sha=digest(package.read_bytes())[:16]
            client=Mock()
            # Existing objects may be on the second page; don't create duplicates.
            client.list_pipelines.side_effect=[
                Obj(pipelines=[Obj(display_name='Autre pipeline')],next_page_token='page2'),
                Obj(pipelines=[Obj(display_name='Prévoir les ventes',pipeline_id='p1')],next_page_token=None)]
            client.list_pipeline_versions.return_value=Obj(pipeline_versions=[
                Obj(display_name='demo-'+sha,pipeline_version_id='v1')],next_page_token=None)
            client.list_experiments.return_value=Obj(experiments=[
                Obj(display_name='Ventes du magasin',experiment_id='e1')],next_page_token=None)
            client.list_runs.return_value=Obj(runs=[
                Obj(display_name=label+' ['+sha[:8]+']',run_id=str(i))
                for i,label in enumerate(['01 - Samedi avec promotion','02 - Samedi sans promotion'])],next_page_token=None)
            client.wait_for_run_completion.return_value=Obj(state=run_state)
            with patch('preparer.get',return_value={'spec':{'host':'pipelines.example.test'}}), \
                 patch('preparer.oc',return_value='test-token'), patch('preparer.kfp.Client',return_value=client):
                if run_state=='SUCCEEDED':
                    ids=ensure_pipeline('demo',package,True)
                    self.assertEqual(ids['example_run_ids'],['0','1'])
                else:
                    with self.assertRaises(RuntimeError):ensure_pipeline('demo',package,True)
            client.upload_pipeline.assert_not_called()
            client.upload_pipeline_version.assert_not_called()
            client.create_experiment.assert_not_called()
            client.run_pipeline.assert_not_called()

    def test_successful_runs_are_reused_across_pages(self):
        self.run_existing('SUCCEEDED')

    def test_failed_run_is_reported_without_creating_more_runs(self):
        self.run_existing('FAILED')

if __name__=='__main__':unittest.main()
