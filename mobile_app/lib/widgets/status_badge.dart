import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../config/theme_tokens.dart';

enum BadgeStyle {
  highMatch,
  moderate,
  urgent,
  neutral,
  activeCase,
}

class StatusBadge extends StatelessWidget {
  final String label;
  final BadgeStyle style;
  final IconData? icon;

  const StatusBadge({
    super.key,
    required this.label,
    this.style = BadgeStyle.neutral,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color border;
    Color textColor;

    switch (style) {
      case BadgeStyle.highMatch:
        bg = AppColors.emeraldBg.withValues(alpha: 0.4);
        border = AppColors.emerald.withValues(alpha: 0.6);
        textColor = AppColors.emerald;
        break;
      case BadgeStyle.moderate:
        bg = AppColors.amberBg.withValues(alpha: 0.4);
        border = AppColors.amber.withValues(alpha: 0.6);
        textColor = AppColors.amber;
        break;
      case BadgeStyle.urgent:
        bg = AppColors.crimsonBg.withValues(alpha: 0.4);
        border = AppColors.crimson.withValues(alpha: 0.6);
        textColor = AppColors.crimson;
        break;
      case BadgeStyle.activeCase:
        bg = AppColors.primary.withValues(alpha: 0.2);
        border = AppColors.primary.withValues(alpha: 0.5);
        textColor = AppColors.primaryHover;
        break;
      case BadgeStyle.neutral:
        bg = AppColors.cardElevated;
        border = AppColors.border;
        textColor = AppColors.textSecondary;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(AppRadius.pill),
        border: Border.all(color: border, width: 1.0),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 12, color: textColor),
            const SizedBox(width: 4),
          ],
          Text(
            label.toUpperCase(),
            style: GoogleFonts.jetBrainsMono(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: textColor,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }
}
