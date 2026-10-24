import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import '../config/theme_tokens.dart';
import '../config/api_config.dart';
import '../services/api_service.dart';
import '../models/user_model.dart';
import '../widgets/tactical_button.dart';
import '../widgets/tactical_card.dart';
import '../widgets/status_badge.dart';

class SettingsScreen extends StatefulWidget {
  final VoidCallback onAuthChanged;
  const SettingsScreen({super.key, required this.onAuthChanged});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final TextEditingController _usernameController = TextEditingController(text: 'investigator');
  final TextEditingController _passwordController = TextEditingController(text: 'investigator123');
  final TextEditingController _urlController = TextEditingController();

  bool _isLoggingIn = false;
  String? _loginError;
  bool _isTestingConnection = false;
  String? _connectionStatus;

  @override
  void initState() {
    super.initState();
    _urlController.text = ApiConfig.baseUrl.replaceAll('/api/v1', '');
  }

  Future<void> _handleLogin() async {
    setState(() {
      _isLoggingIn = true;
      _loginError = null;
    });

    try {
      await ApiService().login(
        _usernameController.text.trim(),
        _passwordController.text.trim(),
      );
      setState(() {
        _isLoggingIn = false;
      });
      widget.onAuthChanged();
    } catch (e) {
      setState(() {
        _loginError = e.toString().replaceAll('Exception: ', '');
        _isLoggingIn = false;
      });
    }
  }

  Future<void> _handleLogout() async {
    await ApiService().logout();
    setState(() {});
    widget.onAuthChanged();
  }

  Future<void> _testConnection() async {
    setState(() {
      _isTestingConnection = true;
      _connectionStatus = null;
    });

    try {
      final target = _urlController.text.trim();
      final healthUrl = Uri.parse('$target/api/v1/health');
      final res = await http.get(healthUrl).timeout(const Duration(seconds: 4));

      if (res.statusCode == 200) {
        await ApiConfig.setBaseUrl(target);
        setState(() {
          _connectionStatus = 'Connected successfully to backend (HTTP 200 OK)';
          _isTestingConnection = false;
        });
      } else {
        setState(() {
          _connectionStatus = 'Server replied with status ${res.statusCode}';
          _isTestingConnection = false;
        });
      }
    } catch (e) {
      setState(() {
        _connectionStatus = 'Connection failed: $e';
        _isTestingConnection = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ApiService().currentUser;

    return Scaffold(
      backgroundColor: AppColors.canvas,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'OFFICER & SYSTEM CONFIG',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
                letterSpacing: 0.5,
              ),
            ),
            Text(
              'Authentication & Server Node Settings',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 10,
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // User Session Card
            TacticalCard(
              backgroundColor: user != null ? AppColors.cardElevated : AppColors.card,
              borderColor: user != null ? AppColors.primary.withValues(alpha: 0.5) : AppColors.border,
              child: user != null ? _buildLoggedInView(user) : _buildLoginForm(),
            ),

            const SizedBox(height: AppSpacing.md),

            // Server Connection Node Card
            TacticalCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'BACKEND SERVER NODE CONFIGURATION',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textSecondary,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Specify target host (e.g. http://10.0.2.2:8000 for Android emulator or your PC Wi-Fi IP http://192.168.x.x:8000)',
                    style: GoogleFonts.plusJakartaSans(fontSize: 12, color: AppColors.textMuted),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _urlController,
                    style: GoogleFonts.jetBrainsMono(fontSize: 13, color: AppColors.textPrimary),
                    decoration: const InputDecoration(
                      labelText: 'Server Base URL',
                      prefixIcon: Icon(Icons.dns_outlined, size: 18, color: AppColors.textMuted),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TacticalButton(
                    label: 'Test & Save Server Node',
                    icon: Icons.network_check,
                    onPressed: _testConnection,
                    isLoading: _isTestingConnection,
                    variant: TacticalButtonVariant.secondary,
                    height: 44,
                  ),
                  if (_connectionStatus != null) ...[
                    const SizedBox(height: 10),
                    Text(
                      _connectionStatus!,
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 11,
                        color: _connectionStatus!.contains('success') ? AppColors.emerald : AppColors.crimson,
                      ),
                    ),
                  ],
                ],
              ),
            ),

            const SizedBox(height: AppSpacing.md),

            // Model Architecture Info
            TacticalCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'COMPUTER VISION ENGINE TELEMETRY',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textSecondary,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 10),
                  _buildSpecRow('Face Detector', 'OpenCV YuNet ONNX (DNN)'),
                  _buildSpecRow('Biometric Representation', 'SFace MobileFaceNet (128-D)'),
                  _buildSpecRow('Normalization', 'L2-Unit Hypersphere (||v|| = 1.0)'),
                  _buildSpecRow('Metric Distance', 'Cosine Dot Product Matrix'),
                  _buildSpecRow('Calibrated Tiers', 'High ≥ 0.70 • Moderate ≥ 0.50'),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLoggedInView(UserModel user) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  user.fullName,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  'Badge: ${user.badgeNumber} • ${user.email}',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
            StatusBadge(
              label: user.role,
              style: BadgeStyle.activeCase,
            ),
          ],
        ),
        const SizedBox(height: 16),
        TacticalButton(
          label: 'Sign Out Officer Session',
          icon: Icons.logout,
          onPressed: _handleLogout,
          variant: TacticalButtonVariant.danger,
          height: 42,
        ),
      ],
    );
  }

  Widget _buildLoginForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'OFFICER AUTHENTICATION',
          style: GoogleFonts.jetBrainsMono(
            fontSize: 11,
            fontWeight: FontWeight.w700,
            color: AppColors.textSecondary,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _usernameController,
          style: GoogleFonts.plusJakartaSans(fontSize: 13, color: AppColors.textPrimary),
          decoration: const InputDecoration(
            labelText: 'Username or Officer ID',
            prefixIcon: Icon(Icons.badge_outlined, size: 18, color: AppColors.textMuted),
          ),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _passwordController,
          obscureText: true,
          style: GoogleFonts.plusJakartaSans(fontSize: 13, color: AppColors.textPrimary),
          decoration: const InputDecoration(
            labelText: 'Password',
            prefixIcon: Icon(Icons.lock_outline, size: 18, color: AppColors.textMuted),
          ),
        ),
        const SizedBox(height: 12),

        // Quick Role Buttons
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: () {
                  _usernameController.text = 'investigator';
                  _passwordController.text = 'investigator123';
                },
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppColors.border),
                  padding: const EdgeInsets.symmetric(vertical: 8),
                ),
                child: Text(
                  'Investigator',
                  style: GoogleFonts.plusJakartaSans(fontSize: 11, color: AppColors.primaryHover),
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: OutlinedButton(
                onPressed: () {
                  _usernameController.text = 'admin';
                  _passwordController.text = 'admin123';
                },
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppColors.border),
                  padding: const EdgeInsets.symmetric(vertical: 8),
                ),
                child: Text(
                  'Admin',
                  style: GoogleFonts.plusJakartaSans(fontSize: 11, color: AppColors.amber),
                ),
              ),
            ),
          ],
        ),

        if (_loginError != null) ...[
          const SizedBox(height: 8),
          Text(
            _loginError!,
            style: const TextStyle(color: AppColors.crimson, fontSize: 12),
          ),
        ],

        const SizedBox(height: 14),

        TacticalButton(
          label: 'Authenticate Officer Session',
          icon: Icons.login,
          onPressed: _isLoggingIn ? null : _handleLogin,
          isLoading: _isLoggingIn,
          variant: TacticalButtonVariant.primary,
          height: 48,
        ),
      ],
    );
  }

  Widget _buildSpecRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: GoogleFonts.plusJakartaSans(fontSize: 12, color: AppColors.textMuted),
          ),
          Text(
            value,
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}
