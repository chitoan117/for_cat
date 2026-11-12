import 'dart:convert';
import 'package:feeder_demo/feeder_state.dart';
import 'package:feeder_demo/history_model.dart';
import 'package:feeder_demo/user_pages.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'real_backend_test.dart' show backend, FakeSocket, until;
import 'state_fixture.dart';

Map<String,dynamic> record() => {'schema_version':2,'final':true,'meal_id':'meal_real_A',
 'food':'FOOD_A','starting_g':35.0,'remaining_g':2.0,'consumed_g':33.0,
 'timestamp':'2026-11-10T00:00:00Z'};
void main(){
 test('real results survive reload and deduplicate a meal; no demo entries',() async{
  final client=MockClient((r)async=>http.Response(jsonEncode({'records':[record(),record(),{'food':'FOOD_A'}]}),200));
  final b=backend(client);addTearDown(b.dispose);
  expect(b.mealPreferenceLogs,isEmpty);
  await b.refreshMealObservation();await b.refreshMealObservation();
  expect(b.mealPreferenceLogs,hasLength(1));expect(b.mealPreferenceLogs.single.id,'meal_real_A');
  expect(b.mealPreferenceLogs.single.consumedGrams,33);expect(b.mealPreferenceLogs.single.isLike,isTrue);
  final other=backend(MockClient((r)async=>http.Response(jsonEncode({'records':[record()]}),200)));
  addTearDown(other.dispose);await other.refreshMealObservation();
  expect(other.mealPreferenceLogs.single.id,'meal_real_A');
 });
 test('ongoing telemetry cannot invent preference history',() async{
  final socket=FakeSocket();
  final b=backend(MockClient((r)async=>http.Response(jsonEncode(r.url.path=='/api/status'?fixture():{'records':[]}),200)),sockets:(_)=>socket);
  addTearDown(b.dispose);await b.start();await until(()=>b.online);
  socket.controller.add(jsonEncode({...fixture(),'meal_schema_version':2,'meal_phase':'OBSERVING',
   'meal_id':'ongoing','meal_preference':'DISLIKE','meal_starting_g':35,'meal_remaining_g':32}));
  expect(b.mealPreferenceLogs,isEmpty);
 });
 test('selection and finishing never issue a feeder or pump command',() async{
  final requests=<String>[];
  final b=backend(MockClient((r)async{
   requests.add('${r.method} ${r.url.path} ${r.body}');return http.Response('{"queued":true,"applied":false}',202);
  }));addTearDown(b.dispose);
  await b.setMealFood('FOOD_B');await b.finishMealObservation();
  expect(requests,hasLength(2));expect(requests[0],contains('SELECT_B'));expect(requests[1],contains('FINISH'));
  expect(requests.every((r)=>r.contains('/api/meal-observation')),isTrue);
  expect(b.selectedFood,'FOOD_A'); // Queued is not yet applied.
 });
 test('same consumption rule applies to A and B and to measured portion size',(){
  expect(evaluateMealPreference(food:'FOOD_B',startingGrams:35,remainingGrams:2).isLike,isTrue);
  expect(evaluateMealPreference(food:'FOOD_A',startingGrams:35,remainingGrams:34).isDislike,isTrue);
  expect(evaluateMealPreference(food:'FOOD_A',startingGrams:70,remainingGrams:50).preference,'MODERATE');
  expect(HistoryEntry.fromEvent({'kind':'meal_preference','details':{'food':'FOOD_A','remaining_g':0}}),isNull);
 });
 testWidgets('mobile meal panel shows live progress without premature result',(tester)async{
  tester.view.physicalSize=const Size(390,844);tester.view.devicePixelRatio=1;addTearDown(tester.view.reset);
  final b=backend(MockClient((r)async=>http.Response('{"records":[]}',200)));addTearDown(b.dispose);
  b.mealObservationSupported=true;
  b.state=FeederState.decode(jsonEncode({...fixture(),'meal_phase':'OBSERVING','meal_food':'FOOD_A',
   'meal_elapsed_seconds':20,'meal_stable':true,'meal_consumed_g':3,'meal_remaining_g':32}));
  await tester.pumpWidget(MaterialApp(home:Scaffold(body:SingleChildScrollView(child:MealPreferencePanel(backend:b)))));
  expect(find.text('Món A'),findsOneWidget);expect(find.text('Món B'),findsOneWidget);
  expect(find.textContaining('Đang theo dõi'),findsOneWidget);
  expect(find.text('Kết thúc lượt thử'),findsOneWidget);expect(find.text('Ít ăn Món A'),findsNothing);
  expect(tester.takeException(),isNull);
 });
}
