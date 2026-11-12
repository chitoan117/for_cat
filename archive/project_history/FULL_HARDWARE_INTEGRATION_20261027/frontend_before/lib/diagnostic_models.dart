import 'feeder_state.dart';
import 'meal_plans.dart';
import 'status_model.dart';

class UltrasonicState {
  final String sensorId, type, role;
  final bool? enabled, wired, valid, timeout, stale;
  final double? distanceCm, ageSeconds;
  final AppStatus state;
  final int? triggerGpio, echoGpio, proposedTrigger, proposedEcho;
  const UltrasonicState({
    required this.sensorId,
    required this.type,
    required this.role,
    required this.state,
    this.enabled,
    this.wired,
    this.valid,
    this.timeout,
    this.stale,
    this.distanceCm,
    this.ageSeconds,
    this.triggerGpio,
    this.echoGpio,
    this.proposedTrigger,
    this.proposedEcho,
  });

  static List<UltrasonicState> fromSystem(FeederState system) => [
    _primary(
      system,
      'hc_sr04_1',
      'HC-SR04',
      'CAT_APPROACH',
      'approach',
      12,
      13,
    ),
    _secondary(system, 'hc_sr04_2', 'HC-SR04', 'food', 16, 17),
    _primary(
      system,
      'jsn_sr04t_1',
      'JSN-SR04T',
      'WATER_LEVEL',
      'water_operational',
      14,
      15,
    ),
    _secondary(system, 'jsn_sr04t_2', 'JSN-SR04T', 'water', 18, 10),
  ];
  static UltrasonicState _primary(
    FeederState s,
    String id,
    String type,
    String role,
    String key,
    int trig,
    int echo,
  ) {
    final data = s.sensor(key), health = text(data['health']);
    final explicit = data['state'];
    AppStatus status = explicit is String
        ? parseStatus(explicit)
        : parseStatus(health);
    bool? configured = data['configured'] is bool
        ? data['configured'] as bool
        : null;
    if (health == 'NOT_CONFIGURED') configured = false;
    if ([
      'HEALTHY',
      'NOT_CALIBRATED',
      'NOT_CONNECTED',
      'TIMEOUT',
    ].contains(health)) {
      configured ??= true;
    }
    final bool? isTimeout = data['timeout'] is bool
        ? data['timeout'] as bool
        : data['valid'] == true
        ? false
        : s.online &&
              configured == true &&
              data['valid'] == false &&
              (health == 'TIMEOUT' ||
                  health == 'NOT_CONNECTED' &&
                      number(data['timeout_count']) != null &&
                      (number(data['timeout_count'])! > 0))
        ? true
        : null;
    if (s.linkHealth == 'UNKNOWN' || s.linkHealth == 'ESP32_DISCONNECTED') {
      status = s.linkHealth == 'UNKNOWN'
          ? AppStatus.unknown
          : AppStatus.offline;
    } else if (s.linkHealth == 'ESP32_STALE') {
      status = AppStatus.stale;
    } else if (data['wired'] == false || health == 'NOT_WIRED') {
      status = AppStatus.notWired;
    } else if (configured == false) {
      status = AppStatus.notConfigured;
    } else if (data['enabled'] == false) {
      status = AppStatus.disabled;
    } else if (data['stale'] == true) {
      status = AppStatus.stale;
    } else if (isTimeout == true) {
      status = AppStatus.timeout;
    } else if (health == 'NOT_CONNECTED') {
      status = AppStatus.unknown;
    }
    return UltrasonicState(
      sensorId: id,
      type: type,
      role: role,
      state: status,
      enabled: data['enabled'] is bool ? data['enabled'] as bool : configured,
      wired: data['wired'] is bool ? data['wired'] as bool : null,
      valid: s.online && data['valid'] is bool ? data['valid'] as bool : null,
      distanceCm:
          [
            AppStatus.stale,
            AppStatus.timeout,
            AppStatus.notWired,
            AppStatus.notConfigured,
            AppStatus.disabled,
          ].contains(status)
          ? null
          : s.distance(key),
      timeout: s.online && configured == true ? isTimeout : null,
      stale: data['stale'] is bool
          ? data['stale'] as bool
          : s.linkHealth == 'ESP32_STALE'
          ? true
          : null,
      ageSeconds: number(data['age_seconds']),
      triggerGpio: trig,
      echoGpio: echo,
    );
  }

  static UltrasonicState _secondary(
    FeederState s,
    String id,
    String type,
    String kind,
    int trig,
    int echo,
  ) {
    final notWired = s.data['${kind}_reservoir_sensor'] == 'NOT_WIRED';
    return UltrasonicState(
      sensorId: id,
      type: type,
      role: 'TBD',
      state: notWired ? AppStatus.notWired : AppStatus.unknown,
      wired: notWired ? false : null,
      enabled: notWired ? false : null,
      proposedTrigger: trig,
      proposedEcho: echo,
    );
  }
}

class AutoCatView {
  final String state;
  final bool supported;
  final Map<String, bool?> checks;
  const AutoCatView(this.state, this.supported, this.checks);
  factory AutoCatView.fromSystem(FeederState system) {
    final raw = object(system.data['auto_cat']),
        supplied = object(object(system.data['auto_cat'])['checks']);
    const allowed = [
      'IDLE',
      'CAT_DETECTED',
      'APPROACHING',
      'READY_TO_REQUEST',
      'BLOCKED',
      'COOLDOWN',
    ];
    final supported = allowed.contains(raw['state']);
    final current = system.online && system.classification != 'UNKNOWN';
    final checks = <String, bool?>{
      for (final key in ['ai', 'distance', 'stable', 'cooldown', 'hx711'])
        key: current && supplied[key] is bool ? supplied[key] as bool : null,
    };
    if (!supported) {
      checks['ai'] = system.classification == 'UNKNOWN'
          ? null
          : system.classification == 'CAT';
      final decisions = object(system.data['decisions']),
          distance = system.distance('approach');
      final threshold = number(decisions['near_threshold_cm']);
      if (decisions['near_configured'] == true &&
          distance != null &&
          threshold != null) {
        checks['distance'] = distance <= threshold;
        checks['stable'] = decisions['near_stable'] is bool
            ? decisions['near_stable'] as bool
            : null;
      }
      if (system.online && system.sensor('weight')['calibrated'] == false) {
        checks['hx711'] = false;
      }
    }
    return AutoCatView(
      supported && current ? raw['state'] as String : 'UNKNOWN',
      supported,
      checks,
    );
  }
}

class NextMeal {
  final MealPlan plan;
  final DateTime dueUtc;
  const NextMeal(this.plan, this.dueUtc);
}

NextMeal? nextMeal(
  List<MealPlan> plans,
  DateTime now,
  Iterable<Map<String, dynamic>> occurrences,
) {
  final local = now.toUtc().add(const Duration(hours: 7));
  NextMeal? best;
  for (final plan in plans.where((p) => p.enabled)) {
    for (var delta = 0; delta <= 7; delta++) {
      final day = DateTime.utc(local.year, local.month, local.day + delta);
      if (!plan.weekdays.contains(day.weekday - 1)) continue;
      final date =
          '${day.year.toString().padLeft(4, '0')}-${day.month.toString().padLeft(2, '0')}-${day.day.toString().padLeft(2, '0')}';
      if (occurrences.any(
        (o) => o['plan_id'] == plan.id && o['local_date'] == date,
      )) {
        continue;
      }
      final time = plan.localTime.split(':');
      final due = DateTime.utc(
        day.year,
        day.month,
        day.day,
        int.parse(time[0]),
        int.parse(time[1]),
      ).subtract(const Duration(hours: 7));
      if (due.isBefore(now.subtract(const Duration(seconds: 60)))) continue;
      if (best == null || due.isBefore(best.dueUtc)) best = NextMeal(plan, due);
      break;
    }
  }
  return best;
}
