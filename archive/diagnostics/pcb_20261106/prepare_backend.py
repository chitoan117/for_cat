from pathlib import Path
import ast,json
r=Path(__file__).parent
# Preserve stable channel IDs for the installed Flutter build. JSN in an ID is legacy only.
replacements={
 "('HC-SR04', 'TBD', 16, 17, 'hc2_cm')":"('HC-SR04', 'FOOD_RESERVOIR', 16, 17, 'hc2_cm')",
 "('JSN-SR04T', 'WATER_LEVEL', 14, 15, 'food_distance_cm')":"('HC-SR04', 'WATER_BOWL', 14, 15, 'food_distance_cm')",
 "('JSN-SR04T', 'TBD', 18, 10, 'water_distance_cm')":"('HC-SR04', 'WATER_RESERVOIR', 18, 19, 'water_distance_cm')",
}
s=(r/'fc_live_bridge.before.py').read_text()
for a,b in replacements.items(): assert a in s;s=s.replace(a,b)
s=s.replace("<= 20.0", "<= 30.0").replace("'near_threshold_cm': 20.0", "'near_threshold_cm': 30.0")
s=s.replace("'water_level_percent': msg.get('water_level_percent'),", """'water_level_percent': msg.get('water_level_percent'),
            'pcb_profile': msg.get('pcb_profile'),
            'food_reservoir_percent': msg.get('food_reservoir_percent'),
            'water_reservoir_percent': msg.get('water_reservoir_percent'),
            'pump_enabled': msg.get('pump_enabled'),
            'pump_running': msg.get('pump_running'),
            'pump_fault': msg.get('pump_fault'),
            'pump_reason': msg.get('pump_reason'),""")
s=s.replace("'pump_armed': False,", "'pump_armed': msg.get('pump_enabled') is True,")
s=s.replace("'pump_state': 'OFF',", "'pump_state': 'ON' if msg.get('pump_running') is True else 'OFF',")
s=s.replace("'auto_water': False,", "'auto_water': msg.get('pump_enabled') is True,")
ast.parse(s);(r/'fc_live_bridge.py').write_text(s)
s=(r/'ultrasonic_state.before.py').read_text()
s=s.replace("'HC-SR04','TBD',16,17", "'HC-SR04','FOOD_RESERVOIR',16,17")
s=s.replace("'JSN-SR04T','WATER_LEVEL',14,15", "'HC-SR04','WATER_BOWL',14,15")
s=s.replace("'JSN-SR04T','TBD',18,10", "'HC-SR04','WATER_RESERVOIR',18,19")
ast.parse(s);(r/'ultrasonic_state.py').write_text(s)
s=(r/'system_state.before.py').read_text()
a=s.index('            # Compute live reservoir percentages')
b=s.index('        return state',a)
s=s[:a]+'''            # Geometry and percentages come from the dedicated calibrated PCB sensors.
            # Never invent the former 5cm/35cm container dimensions or use bowl % for tank.
            us = state.get('ultrasonic') or {}
            def calibrated_pct(key, channel):
                p=fc.get(key)
                if (fc.get('pcb_profile') == 'HCSR04_E1_E2_D1_D2_V1'
                    and (us.get(channel) or {}).get('valid') is True
                    and type(p) in (int,float) and math.isfinite(p) and 0 <= p <= 100):
                    return round(float(p),1)
                return None
            food_pct=calibrated_pct('food_reservoir_percent','HC_SR04_2')
            tank_pct=calibrated_pct('water_reservoir_percent','JSN_SR04T_2')
            bowl_pct=calibrated_pct('water_level_percent','JSN_SR04T_1')
            state['food_reservoir_percent']=food_pct
            state['water_reservoir_percent']=tank_pct
            state['water_bowl_percent']=bowl_pct
            state['food_reservoir_sensor']='HEALTHY' if food_pct is not None else 'UNKNOWN'
            state['water_reservoir_sensor']='HEALTHY' if tank_pct is not None else 'UNKNOWN'
            state['water_refill_needed']=tank_pct <= 0 if tank_pct is not None else None
            state['water_pump_reason']=fc.get('pump_reason')
'''+s[b:]
ast.parse(s);(r/'system_state.py').write_text(s)
d=json.loads((r/'hardware_current.before.json').read_text())
for k,role,trig,echo,label in [('HC_SR04_1','CAT_APPROACH',12,13,'E1'),('HC_SR04_2','FOOD_RESERVOIR',16,17,'E2'),('JSN_SR04T_1','WATER_BOWL',14,15,'D1'),('JSN_SR04T_2','WATER_RESERVOIR',18,19,'D2')]:
 d['ultrasonic_inventory'][k].update(type='HC-SR04',role=role,trigger_gpio=trig,echo_gpio=echo,pcb_label=label)
(r/'hardware_current.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared backend; syntax PASS. Not deployed pending commissioning.')
