import base64
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'ventes/scripts'))
from reconcile import merge_owned, reconcile

class ReconciliationTests(unittest.TestCase):
    def test_webhook_injection_survives_noop_and_resource_update(self):
        desired = {'containers': [{'name':'atelier', 'image':'image:v1', 'resources':{'limits':{'cpu':'2'}},
                                   'env':[{'name':'DEMO','value':'yes'}]}]}
        live = deepcopy(desired)
        live['containers'][0]['env'].append({'name':'AUTH','value':'injected'})
        live['containers'].append({'name':'kube-rbac-proxy','image':'proxy:v1'})
        live['serviceAccountName'] = 'generated'
        self.assertEqual(merge_owned(live, desired), live)
        desired['containers'][0]['resources']['limits']['cpu'] = '3'
        updated = merge_owned(live, desired)
        self.assertEqual(updated['containers'][1], live['containers'][1])
        self.assertEqual(updated['containers'][0]['env'], live['containers'][0]['env'])
        self.assertEqual(updated['containers'][0]['resources']['limits']['cpu'], '3')
        self.assertEqual(merge_owned(updated, desired), updated)

    def test_existing_secret_is_not_rewritten(self):
        wanted = {'apiVersion':'v1','kind':'Secret','metadata':{'name':'connection','namespace':'demo'},
                  'stringData':{'AWS_SECRET_ACCESS_KEY':'test-value'}}
        current = deepcopy(wanted)
        current.pop('stringData')
        current['data']={'AWS_SECRET_ACCESS_KEY':base64.b64encode(b'test-value').decode()}
        current['metadata']['resourceVersion']='42'
        with patch('reconcile.get', return_value=current), patch('reconcile.oc') as command:
            self.assertFalse(reconcile(wanted))
            command.assert_not_called()

    def test_patch_uses_resource_version_for_concurrent_edits(self):
        wanted = {'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'demo','namespace':'demo'},'data':{'a':'new'}}
        current = deepcopy(wanted)
        current['data']={'a':'old','unrelated':'keep'}
        current['metadata']['resourceVersion']='42'
        import json
        with patch('reconcile.get', return_value=current), patch('reconcile.oc') as command:
            self.assertTrue(reconcile(wanted))
            payload=json.loads(command.call_args.kwargs['data'])
            self.assertEqual(payload['metadata']['resourceVersion'],'42')
            self.assertEqual(payload['data']['unrelated'],'keep')

if __name__ == '__main__':
    unittest.main()
