import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../config/theme_tokens.dart';

enum TacticalButtonVariant {
  primary,
  emerald,
  secondary,
  danger,
}

class TacticalButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool isLoading;
  final TacticalButtonVariant variant;
  final double? width;
  final double height;

  const TacticalButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.isLoading = false,
    this.variant = TacticalButtonVariant.primary,
    this.width,
    this.height = 48.0,
  });

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color border;
    Color textColor = AppColors.textPrimary;

    switch (variant) {
      case TacticalButtonVariant.primary:
        bg = AppColors.primary;
        border = AppColors.primary;
        textColor = Colors.white;
        break;
      case TacticalButtonVariant.emerald:
        bg = AppColors.emerald;
        border = AppColors.emerald;
        textColor = Colors.white;
        break;
      case TacticalButtonVariant.secondary:
        bg = AppColors.cardElevated;
        border = AppColors.border;
        textColor = AppColors.textPrimary;
        break;
      case TacticalButtonVariant.danger:
        bg = AppColors.crimson;
        border = AppColors.crimson;
        textColor = Colors.white;
        break;
    }

    if (onPressed == null) {
      bg = bg.withValues(alpha: 0.5);
      border = border.withValues(alpha: 0.5);
      textColor = textColor.withValues(alpha: 0.6);
    }

    return SizedBox(
      width: width,
      height: height,
      child: Material(
        color: bg,
        borderRadius: BorderRadius.circular(AppRadius.md),
        child: InkWell(
          onTap: isLoading ? null : onPressed,
          borderRadius: BorderRadius.circular(AppRadius.md),
          splashColor: Colors.white10,
          highlightColor: Colors.white12,
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(color: border, width: 1.0),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 16),
            alignment: Alignment.center,
            child: isLoading
                ? SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(textColor),
                    ),
                  )
                : Row(
                    mainAxisSize: MainAxisSize.min,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      if (icon != null) ...[
                        Icon(icon, size: 18, color: textColor),
                        const SizedBox(width: 8),
                      ],
                      Text(
                        label,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: textColor,
                          letterSpacing: 0.2,
                        ),
                      ),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}
