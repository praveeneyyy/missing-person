import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../config/theme_tokens.dart';
import '../services/api_service.dart';
import 'scanner_screen.dart';
import 'cases_screen.dart';
import 'report_sighting_screen.dart';
import 'receipt_wallet_screen.dart';
import 'settings_screen.dart';

class MainShellScreen extends StatefulWidget {
  const MainShellScreen({super.key});

  @override
  State<MainShellScreen> createState() => _MainShellScreenState();
}

class _MainShellScreenState extends State<MainShellScreen> {
  int _currentIndex = 0;

  void _onAuthChanged() {
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final user = ApiService().currentUser;

    final List<Widget> screens = [
      const ScannerScreen(),
      const CasesScreen(),
      const ReportSightingScreen(),
      const ReceiptWalletScreen(),
      SettingsScreen(onAuthChanged: _onAuthChanged),
    ];

    return Scaffold(
      backgroundColor: AppColors.canvas,
      body: IndexedStack(
        index: _currentIndex,
        children: screens,
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: AppColors.card,
          border: Border(
            top: BorderSide(color: AppColors.border, width: 1.0),
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: BottomNavigationBar(
              currentIndex: _currentIndex,
              onTap: (index) {
                setState(() {
                  _currentIndex = index;
                });
              },
              backgroundColor: Colors.transparent,
              elevation: 0,
              type: BottomNavigationBarType.fixed,
              selectedItemColor: AppColors.primaryHover,
              unselectedItemColor: AppColors.textMuted,
              selectedLabelStyle: GoogleFonts.plusJakartaSans(
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
              unselectedLabelStyle: GoogleFonts.plusJakartaSans(
                fontSize: 11,
                fontWeight: FontWeight.w500,
              ),
              items: [
                const BottomNavigationBarItem(
                  icon: Icon(Icons.document_scanner_outlined),
                  activeIcon: Icon(Icons.document_scanner),
                  label: 'Scanner',
                ),
                const BottomNavigationBarItem(
                  icon: Icon(Icons.folder_shared_outlined),
                  activeIcon: Icon(Icons.folder_shared),
                  label: 'Cases',
                ),
                const BottomNavigationBarItem(
                  icon: Icon(Icons.add_photo_alternate_outlined),
                  activeIcon: Icon(Icons.add_photo_alternate),
                  label: 'Sighting',
                ),
                const BottomNavigationBarItem(
                  icon: Icon(Icons.receipt_long_outlined),
                  activeIcon: Icon(Icons.receipt_long),
                  label: 'Receipts',
                ),
                BottomNavigationBarItem(
                  icon: Icon(user != null ? Icons.verified_user_outlined : Icons.tune_outlined),
                  activeIcon: Icon(user != null ? Icons.verified_user : Icons.tune),
                  label: user != null ? 'Officer' : 'Config',
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
