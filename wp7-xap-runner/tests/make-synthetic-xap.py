#!/usr/bin/env python3
import argparse, pathlib, zipfile

p=argparse.ArgumentParser()
p.add_argument('--assembly', required=True)
p.add_argument('--out', required=True)
a=p.parse_args()
assembly=pathlib.Path(a.assembly)
out=pathlib.Path(a.out)
out.parent.mkdir(parents=True, exist_ok=True)

app_manifest='''<Deployment xmlns="http://schemas.microsoft.com/client/2007/deployment"
 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
 EntryPointAssembly="SampleWp7App"
 EntryPointType="SampleWp7App.App"
 RuntimeVersion="4.0.50826.0">
 <Deployment.Parts>
   <AssemblyPart x:Name="SampleWp7App" Source="SampleWp7App.dll" />
 </Deployment.Parts>
</Deployment>'''

wm='''<Deployment xmlns="http://schemas.microsoft.com/windowsphone/2009/deployment" AppPlatformVersion="7.1">
 <App xmlns="" ProductID="{11111111-2222-3333-4444-555555555555}" Title="XAPSCAN1 Synthetic" RuntimeType="Silverlight" Version="1.0.0.0" Genre="apps.normal" Author="OpenAI" Description="CI fixture" AppPlatformVersion="7.1">
   <Capabilities><Capability Name="ID_CAP_NETWORKING" /></Capabilities>
   <Tasks><DefaultTask Name="_default" NavigationPage="MainPage.xaml" /></Tasks>
 </App>
</Deployment>'''

with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('AppManifest.xaml', app_manifest)
    z.writestr('WMAppManifest.xml', wm)
    z.writestr('MainPage.xaml', '<Grid xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"/>')
    z.write(assembly, 'SampleWp7App.dll')
print(out)
