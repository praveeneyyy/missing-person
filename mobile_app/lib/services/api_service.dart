import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';
import '../models/user_model.dart';
import '../models/case_model.dart';
import '../models/match_result_model.dart';
import '../models/sighting_receipt_model.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  UserModel? _currentUser;
  String? _token;

  UserModel? get currentUser => _currentUser;
  String? get token => _token;
  bool get isAuthenticated => _token != null && _currentUser != null;

  Map<String, String> get _authHeaders {
    final headers = {'Content-Type': 'application/json', 'Accept': 'application/json'};
    if (_token != null) {
      headers['Authorization'] = 'Bearer $_token';
    }
    return headers;
  }

  Future<void> init() async {
    await ApiConfig.init();
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('auth_token');
    final userJson = prefs.getString('user_profile');
    if (userJson != null) {
      try {
        _currentUser = UserModel.fromJson(jsonDecode(userJson), token: _token);
      } catch (_) {
        _currentUser = null;
      }
    }
  }

  Future<UserModel> login(String username, String password) async {
    final response = await http.post(
      Uri.parse(ApiConfig.loginUrl),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'password': password}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      _token = data['access_token'];
      _currentUser = UserModel.fromJson(data['user'], token: _token);

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('auth_token', _token!);
      await prefs.setString('user_profile', jsonEncode(data['user']));

      return _currentUser!;
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Authentication failed');
    }
  }

  Future<void> logout() async {
    _token = null;
    _currentUser = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    await prefs.remove('user_profile');
  }

  Future<List<CaseModel>> getCases() async {
    final response = await http.get(
      Uri.parse(ApiConfig.casesUrl),
      headers: _authHeaders,
    );

    if (response.statusCode == 200) {
      final List raw = jsonDecode(response.body);
      return raw.map((item) => CaseModel.fromJson(item)).toList();
    } else {
      throw Exception('Failed to fetch cases: ${response.statusCode}');
    }
  }

  Future<CaseModel> getCaseDetail(int id) async {
    final response = await http.get(
      Uri.parse('${ApiConfig.casesUrl}/$id'),
      headers: _authHeaders,
    );

    if (response.statusCode == 200) {
      return CaseModel.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Case not found');
    }
  }

  Future<MatchResponse> matchProbePhoto(Uint8List imageBytes, String filename) async {
    final uri = Uri.parse(ApiConfig.matchGalleryUrl);
    final request = http.MultipartRequest('POST', uri);

    if (_token != null) {
      request.headers['Authorization'] = 'Bearer $_token';
    }

    request.files.add(
      http.MultipartFile.fromBytes(
        'photo',
        imageBytes,
        filename: filename,
      ),
    );

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return MatchResponse.fromJson(data);
    } else {
      final err = jsonDecode(response.body);
      throw Exception(err['detail'] ?? 'Facial biometric comparison failed');
    }
  }

  Future<String> submitSighting({
    required Uint8List imageBytes,
    required String filename,
    required String locationName,
    double? latitude,
    double? longitude,
    String? notes,
  }) async {
    final uri = Uri.parse(ApiConfig.sightingsSubmitUrl);
    final request = http.MultipartRequest('POST', uri);

    request.fields['location_name'] = locationName;
    if (latitude != null) request.fields['latitude'] = latitude.toString();
    if (longitude != null) request.fields['longitude'] = longitude.toString();
    if (notes != null && notes.isNotEmpty) request.fields['notes'] = notes;

    request.files.add(
      http.MultipartFile.fromBytes(
        'photo',
        imageBytes,
        filename: filename,
      ),
    );

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200 || response.statusCode == 201) {
      final data = jsonDecode(response.body);
      return data['receipt_number'] ?? 'STG-2026-CONFIRMED';
    } else {
      final err = jsonDecode(response.body);
      throw Exception(err['detail'] ?? 'Sighting submission failed');
    }
  }

  Future<SightingReceiptModel> lookupReceipt(String receiptNumber) async {
    final clean = receiptNumber.trim().toUpperCase();
    final response = await http.get(
      Uri.parse('${ApiConfig.sightingsLookupUrl}/$clean'),
      headers: {'Accept': 'application/json'},
    );

    if (response.statusCode == 200) {
      return SightingReceiptModel.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Receipt not found or invalid');
    }
  }

  Future<List<dynamic>> getSurveillanceAlerts() async {
    final response = await http.get(
      Uri.parse(ApiConfig.alertsUrl),
      headers: _authHeaders,
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    } else {
      throw Exception('Failed to fetch surveillance alerts');
    }
  }
}

