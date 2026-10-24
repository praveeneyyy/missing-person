import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Tactical Elegance & Purposeful Minimalism
/// Design system tokens for Law Enforcement Biometrics & Field Intelligence.
class AppColors {
  // Deep Obsidian & Slate Canvas
  static const Color canvas = Color(0xFF0B0F17);
  static const Color card = Color(0xFF121824);
  static const Color cardElevated = Color(0xFF182232);
  static const Color cardSubtle = Color(0xFF0F1420);

  // Micro-Borders & Architectural Dividers
  static const Color border = Color(0xFF1E293B);
  static const Color borderFocus = Color(0xFF334155);
  static const Color borderHighlight = Color(0xFF2563EB);

  // Professional Accents
  static const Color primary = Color(0xFF2563EB); // Deep Sapphire
  static const Color primaryHover = Color(0xFF3B82F6);
  static const Color primaryLight = Color(0xFF1D4ED8);

  // Calibrated Semantic Status Accents
  static const Color emerald = Color(0xFF10B981); // Verified Hit (≥ 0.70)
  static const Color emeraldBg = Color(0xFF064E3B);
  static const Color amber = Color(0xFFF59E0B); // Moderate Review (≥ 0.50)
  static const Color amberBg = Color(0xFF78350F);
  static const Color crimson = Color(0xFFEF4444); // Urgent / Rejected
  static const Color crimsonBg = Color(0xFF7F1D1D);
  static const Color slate = Color(0xFF64748B); // Neutral Info

  // High-Contrast Typography
  static const Color textPrimary = Color(0xFFF8FAFC); // 98% crisp white
  static const Color textSecondary = Color(0xFF94A3B8); // Balanced slate
  static const Color textMuted = Color(0xFF64748B); // Dim metadata
  static const Color textOnAccent = Color(0xFFFFFFFF);
}

class AppSpacing {
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 16.0;
  static const double lg = 24.0;
  static const double xl = 32.0;
  static const double xxl = 48.0;
}

class AppRadius {
  static const double sm = 8.0;
  static const double md = 12.0;
  static const double lg = 16.0;
  static const double pill = 999.0;
}

class AppTheme {
  static ThemeData get darkTheme {
    final textTheme = GoogleFonts.plusJakartaSansTextTheme(
      ThemeData.dark().textTheme,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppColors.canvas,
      primaryColor: AppColors.primary,
      canvasColor: AppColors.canvas,
      cardColor: AppColors.card,
      dividerColor: AppColors.border,
      textTheme: textTheme.copyWith(
        displayLarge: GoogleFonts.plusJakartaSans(
          fontSize: 28,
          fontWeight: FontWeight.w700,
          color: AppColors.textPrimary,
          letterSpacing: -0.5,
        ),
        headlineMedium: GoogleFonts.plusJakartaSans(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
          letterSpacing: -0.2,
        ),
        titleMedium: GoogleFonts.plusJakartaSans(
          fontSize: 16,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
        ),
        bodyLarge: GoogleFonts.plusJakartaSans(
          fontSize: 14,
          fontWeight: FontWeight.w400,
          color: AppColors.textPrimary,
          height: 1.5,
        ),
        bodyMedium: GoogleFonts.plusJakartaSans(
          fontSize: 13,
          fontWeight: FontWeight.w400,
          color: AppColors.textSecondary,
          height: 1.4,
        ),
        labelSmall: GoogleFonts.jetBrainsMono(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: AppColors.textMuted,
          letterSpacing: 0.5,
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.canvas,
        elevation: 0,
        centerTitle: false,
        scrolledUnderElevation: 0,
        iconTheme: IconThemeData(color: AppColors.textPrimary),
      ),
      cardTheme: CardThemeData(
        color: AppColors.card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          side: const BorderSide(color: AppColors.border, width: 1.0),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.card,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        hintStyle: GoogleFonts.plusJakartaSans(
          color: AppColors.textMuted,
          fontSize: 14,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.border, width: 1.0),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.border, width: 1.0),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: AppColors.card,
        selectedItemColor: AppColors.primaryHover,
        unselectedItemColor: AppColors.textMuted,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
      ),
    );
  }
}
