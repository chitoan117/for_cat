from pathlib import Path
root=Path(__file__).resolve().parent
p=Path('D:/DA_KT_NC/feeder_demo/test/live_camera_test.dart')
old=(root/'live_camera_test.before.dart').read_bytes()
s=old.decode('utf-8').replace('\r\n','\n').replace('overview backend notifications preserve active camera state','overview omits camera before and after backend notifications')
a=s.index("    await tester.scrollUntilVisible(find.text('Xem camera'), 200);")
b=s.index("    backend.connectionError",a)
s=s[:a]+"    expect(find.byType(LiveCameraPanel), findsNothing);\n    expect(find.text('Xem camera'), findsNothing);\n"+s[b:]
first_end=s.index("  test(\n",a)
s=s[:first_end].replace("    expect(find.text('Trực tiếp · SIMULATED'), findsOneWidget);", "    expect(find.byType(LiveCameraPanel), findsNothing);")+s[first_end:]
p.write_bytes(s.encode('utf-8'))
print('Updated existing overview-camera expectation to match requested removal.')
