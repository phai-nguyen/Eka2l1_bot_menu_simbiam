#!/usr/bin/env python3
import json, pathlib, sys

r=json.loads(pathlib.Path(sys.argv[1]).read_text())

assert r['scanner']=='XAPSCAN1'
assert r['package']['sha256']=='69bd93627f4fa2c567748e36c3487c083db95c0efe01ef203bf60179bf9342a1'
assert r['appManifest']['runtimeVersion']=='3.0'
assert r['appManifest']['entryPointAssembly']=='Aleterated'
assert r['appManifest']['entryPointType']=='Aleterated.Game1'
assert r['wmAppManifest']['runtimeType']=='XNA'
assert r['entryPoint']['assemblyResolved'] is True
assert r['entryPoint']['typeResolved'] is True

tags=set(r['compatibilityTags'])
assert {'NEEDS_XNA_FULL','SILVERLIGHT','WP7_PHONE_API'} <= tags

main=next(a for a in r['assemblies'] if a['name']=='Aleterated')
assert main['isManaged'] is True
assert main['isIlOnly'] is True
assert main['isMixedMode'] is False

refs={(x['name'],x['version']) for x in main['assemblyReferences']}
assert ('Microsoft.Xna.Framework','4.0.0.0') in refs
assert ('Microsoft.Xna.Framework.Game','4.0.0.0') in refs
assert ('Microsoft.Xna.Framework.Graphics','4.0.0.0') in refs
assert ('Microsoft.Xna.Framework.Input.Touch','4.0.0.0') in refs

phone_refs=set()
for a in r['assemblies']:
    for x in a.get('assemblyReferences',[]):
        if x['name']=='Microsoft.Phone':
            phone_refs.add(x['version'])
assert '7.0.0.0' in phone_refs

codes={x['code'] for x in r['findings']}
assert 'XNA_GRAPHICS_REQUIRED' in codes
assert 'PINVOKE_PRESENT' not in codes
assert 'MIXED_MODE_IMAGE' not in codes

print('XAPSCAN1 real WP7 XNA contract: PASS')
