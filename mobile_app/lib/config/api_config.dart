import 'package:shared_preferences/shared_preferences.dart';

class ApiConfig {
  static const String keyBaseUrl = 'custom_base_url';
  
  // Default endpoints
  // 10.0.2.2 is localhost inside Android emulator
  // 127.0.0.1 is localhost for desktop/web
  static const String defaultEmulatorUrl = 'http://10.0.2.2:8000/api/v1';
  static const String defaultLocalhostUrl = 'http://127.0.0.1:8000/api/v1';

  static String _currentBaseUrl = defaultLocalhostUrl;

  static String get baseUrl => _currentBaseUrl;

  static Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _currentBaseUrl = prefs.getString(keyBaseUrl) ?? defaultLocalhostUrl;
  }

  static Future<void> setBaseUrl(String newUrl) async {
    String cleanUrl = newUrl.trim();
    if (cleanUrl.endsWith('/')) {
      cleanUrl = cleanUrl.substring(0, cleanUrl.length - 1);
    }
    if (!cleanUrl.endsWith('/api/v1')) {
      cleanUrl = '$cleanUrl/api/v1';
    }
    _currentBaseUrl = cleanUrl;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(keyBaseUrl, cleanUrl);
  }

  // Endpoints
  static String get loginUrl => '$_currentBaseUrl/auth/login';
  static String get casesUrl => '$_currentBaseUrl/cases';
  static String get sightingsSubmitUrl => '$_currentBaseUrl/sightings/submit';
  static String get sightingsLookupUrl => '$_currentBaseUrl/sightings/lookup';
  static String get matchGalleryUrl => '$_currentBaseUrl/cases/match-gallery';
  static String get alertsUrl => '$_currentBaseUrl/surveillance/alerts';
  static String get auditUrl => '$_currentBaseUrl/audit';
}
