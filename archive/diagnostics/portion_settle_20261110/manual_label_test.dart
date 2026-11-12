import 'dart:convert';
import 'package:feeder_demo/history_model.dart';
import 'package:feeder_demo/user_pages.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'real_backend_test.dart' show backend;

void main(){
 test('manual removal retains LIKE result without claiming real cat preference',(){
  final m=evaluateMealPreference(food:'FOOD_A',startingGrams:35.16,remainingGrams:0,isManualTest:true);
  expect(m.preference,'LIKE');expect(m.isManualTest,isTrue);expect(m.conclusion,'Kiểm thử Món A: LIKE');
  expect(m.toJson()['observation_mode'],'MANUAL_TEST');expect(m.ruleExplanation,contains('bằng tay'));
 });
 test('manual provenance is preserved after loading persisted record and generic history',()async{
  final record={'schema_version':2,'final':true,'meal_id':'manual_A','food':'FOOD_A','starting_g':35.16,
   'remaining_g':0,'timestamp':'2026-11-10T00:59:47Z','observation_mode':'MANUAL_TEST'};
  final b=backend(MockClient((r)async=>http.Response(jsonEncode({'records':[record]}),200)));addTearDown(b.dispose);
  await b.refreshMealObservation();expect(b.mealPreferenceLogs.single.isManualTest,isTrue);
  final h=HistoryEntry.fromEvent({'kind':'meal_preference','details':record,'timestamp':record['timestamp']});
  expect(h!.title,'Kiểm thử Món A: LIKE');expect(h.source,'MANUAL_TEST');
 });
 testWidgets('manual test card never says that the cat ate the removed food',(tester)async{
  final b=backend(MockClient((r)async=>http.Response('{}',200)));addTearDown(b.dispose);
  b.mealPreferenceLogs.add(evaluateMealPreference(food:'FOOD_A',startingGrams:35,remainingGrams:0,isManualTest:true));
  await tester.pumpWidget(MaterialApp(home:Scaffold(body:SingleChildScrollView(child:MealPreferencePanel(backend:b,compact:true)))));
  expect(find.text('Kiểm thử Món A · LIKE'),findsOneWidget);
  expect(find.textContaining('Lấy ra 35.0 g'),findsOneWidget);
  expect(find.text('Thích Món A'),findsNothing);expect(tester.takeException(),isNull);
 });
}
