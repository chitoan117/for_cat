enum AppStatus {
  online,
  offline,
  healthy,
  unknown,
  stale,
  timeout,
  notWired,
  notConfigured,
  disabled,
  notCalibrated,
  dryRun,
  blocked,
  unstable,
  notAvailable,
}

extension AppStatusText on AppStatus {
  String get code => switch (this) {
    AppStatus.notWired => 'NOT_WIRED',
    AppStatus.notConfigured => 'NOT_CONFIGURED',
    AppStatus.notCalibrated => 'NOT_CALIBRATED',
    AppStatus.dryRun => 'DRY_RUN',
    AppStatus.notAvailable => 'NOT_AVAILABLE',
    _ => name.toUpperCase(),
  };
  String get label => switch (this) {
    AppStatus.online => 'Đang kết nối',
    AppStatus.offline => 'Mất kết nối',
    AppStatus.healthy => 'Hoạt động bình thường',
    AppStatus.unknown => 'Chưa rõ trạng thái',
    AppStatus.stale => 'Dữ liệu đã cũ',
    AppStatus.timeout => 'Không nhận được phản hồi',
    AppStatus.notWired => 'Chưa đấu nối',
    AppStatus.notConfigured => 'Chưa hoàn tất cấu hình',
    AppStatus.disabled => 'Đang tắt',
    AppStatus.notCalibrated => 'Chưa hiệu chuẩn',
    AppStatus.dryRun => 'Chạy thử yêu cầu',
    AppStatus.blocked => 'Bị chặn',
    AppStatus.unstable => 'Chưa ổn định',
    AppStatus.notAvailable => 'Chưa khả dụng',
  };
}

AppStatus parseStatus(Object? raw) => switch (raw) {
  'ONLINE' || 'ESP32_CONNECTED' || 'RUNNING' => AppStatus.online,
  'OFFLINE' || 'DISCONNECTED' || 'ESP32_DISCONNECTED' => AppStatus.offline,
  'HEALTHY' || 'STABLE' || 'CALIBRATED' => AppStatus.healthy,
  'STALE' || 'ESP32_STALE' => AppStatus.stale,
  'TIMEOUT' => AppStatus.timeout,
  'NOT_WIRED' => AppStatus.notWired,
  'NOT_CONFIGURED' || 'THRESHOLDS_UNCONFIGURED' => AppStatus.notConfigured,
  'DISABLED' || 'STOPPED' || 'PLAN_DISABLED' => AppStatus.disabled,
  'NOT_CALIBRATED' ||
  'DEFERRED' ||
  'CANDIDATE_PENDING_VALIDATION' => AppStatus.notCalibrated,
  'DRY_RUN' || 'DRY_RUN_ONLY' => AppStatus.dryRun,
  'BLOCKED' || 'DRY_RUN_BLOCKED' || 'UNATTENDED_SAFE_MODE' => AppStatus.blocked,
  'UNSTABLE' => AppStatus.unstable,
  'NOT_AVAILABLE' || 'UNSUPPORTED' => AppStatus.notAvailable,
  _ => AppStatus.unknown,
};

String reasonText(Object? code) => switch (code) {
  'WEIGHT_NOT_CALIBRATED' => 'Cân chưa hiệu chuẩn',
  'UNATTENDED_SAFE_MODE' => 'Chế độ an toàn đang khóa cơ cấu',
  'TIME_INVALID' => 'Giờ Jetson chưa được xác nhận',
  'NOT_DUE' => 'Chưa đến giờ',
  'PLAN_DISABLED' => 'Lịch đang tắt',
  'NOT_SCHEDULED_TODAY' => 'Không có lịch vào ngày này',
  'MISSED_WINDOW_NO_CATCHUP' => 'Đã qua cửa sổ đến hạn; không chạy bù',
  'ESP32_UNAVAILABLE_NO_QUEUE' => 'ESP32 chưa sẵn sàng',
  'SAFETY_STATE_UNKNOWN_OR_UNSAFE_NO_QUEUE' =>
    'Trạng thái an toàn chưa cho phép',
  'DUE_INSTANCE_DRY_RUN' => 'Đã xét lượt đến hạn',
  'COOLDOWN' => 'Đang trong thời gian chờ',
  'QUEUED' => 'Đang chờ arbiter',
  null || '' || 'UNKNOWN' => 'Chưa có kết quả',
  _ => code is String ? code : 'Chưa có kết quả',
};
