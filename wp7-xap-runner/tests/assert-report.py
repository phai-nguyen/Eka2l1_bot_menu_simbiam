#!/usr/bin/env python3
import json, pathlib, sys

r=json.loads(pathlib.Path(sys.argv[1]).read_text())
assert r['scanner']=='XAPSCAN1'
assert r['appManifest']['entryPointAssembly']=='SampleWp7App'
assert r['appManifest']['entryPointType']=='SampleWp7App.App'
assert r['wmAppManifest']['runtimeType']=='Silverlight'
assert r['wmAppManifest']['navigationPage']=='MainPage.xaml'
assert 'ID_CAP_NETWORKING' in r['wmAppManifest']['capabilities']
assert r['entryPoint']['assemblyResolved'] is True
assert r['entryPoint']['typeResolved'] is True
asm=next(a for a in r['assemblies'] if a['name']=='SampleWp7App')
assert asm['isManaged'] is True
assert asm['isIlOnly'] is True
assert 'SampleWp7App.App' in asm['typeDefinitions']
print('XAPSCAN1 synthetic contract: PASS')
