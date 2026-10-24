import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'config/theme_tokens.dart';
import 'services/api_service.dart';
import 'screens/main_shell_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Dark navigation & status bar
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      systemNavigationBarColor: AppColors.canvas,
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );

  // Initialize API service, tokens, and endpoints
  await ApiService().init();

  runApp(const BiometricFieldApp());
}

class BiometricFieldApp extends StatelessWidget {
  const BiometricFieldApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Biometric Field Surveillance',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: const MainShellScreen(),
    );
  }
}
