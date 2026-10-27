import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

export '../shared/widgets/brand_app_bar.dart';
export '../shared/widgets/error_view.dart';
export '../shared/widgets/offline_banner.dart';
export '../shared/widgets/primary_button.dart';

// ── Brand Palette ─────────────────────────────────────────────────────────────
class AppColors {
  AppColors._();

  // Core brand
  static const primaryGreen = Color(0xFF7DC832); // buttons, highlights, active
  static const darkGreen    = Color(0xFF1A5C2A); // dark surfaces, dark mode bg
  static const darkNavy     = Color(0xFF1A1F3A); // primary text, headers
  static const white        = Color(0xFFFFFFFF); // light surfaces

  // Semantic helpers
  static const success = Color(0xFF7DC832);
  static const error   = Color(0xFFEF4444);
  static const warning = Color(0xFFF59E0B);
  static const info    = Color(0xFF3B82F6);

  // Surface helpers
  static const lightSurface = white;
  static const darkSurface  = darkGreen;

  // Text helpers
  static const lightText = darkNavy;
  static const darkText  = white;

  // ── Backward-compat aliases for pre-existing screens ────────────────────
  // These map old FuelLink names to MedaZone equivalents so legacy screens
  // continue to compile until they are refactored in later tasks.
  static const primary    = primaryGreen;
  static const primaryDark= darkGreen;
  static const accent     = primaryGreen;

  static const green    = primaryGreen;
  static const greenBg  = Color(0x337DC832);
  static const red      = error;
  static const redBg    = Color(0x1FEF4444);
  static const orange   = warning;
  static const orangeBg = Color(0x1FF59E0B);

  static const bgBase    = darkGreen;
  static const bgSurface = Color(0xFF235C34);
  static const bgCard    = Color(0xFF2A6B3E);
  static const border    = Color(0x33FFFFFF);

  static const textPrimary   = white;
  static const textSecondary = Color(0xFFCBD5E0);
  static const textMuted     = Color(0xFF9DC4A8);
}

// ── Text Themes ───────────────────────────────────────────────────────────────
// Req 18.7: bold italic for headings, regular for body
TextTheme _buildTextTheme(Color primaryTextColor, Color secondaryTextColor) {
  return TextTheme(
    // Headings — bold italic per brand spec
    displayLarge: GoogleFonts.inter(
      fontSize: 32,
      fontWeight: FontWeight.w700,
      fontStyle: FontStyle.italic,
      color: primaryTextColor,
      letterSpacing: -0.5,
    ),
    displayMedium: GoogleFonts.inter(
      fontSize: 28,
      fontWeight: FontWeight.w700,
      fontStyle: FontStyle.italic,
      color: primaryTextColor,
    ),
    displaySmall: GoogleFonts.inter(
      fontSize: 24,
      fontWeight: FontWeight.w700,
      fontStyle: FontStyle.italic,
      color: primaryTextColor,
    ),
    headlineLarge: GoogleFonts.inter(
      fontSize: 22,
      fontWeight: FontWeight.w700,
      fontStyle: FontStyle.italic,
      color: primaryTextColor,
    ),
    headlineMedium: GoogleFonts.inter(
      fontSize: 20,
      fontWeight: FontWeight.w700,
      fontStyle: FontStyle.italic,
      color: primaryTextColor,
    ),
    headlineSmall: GoogleFonts.inter(
      fontSize: 18,
      fontWeight: FontWeight.w700,
      fontStyle: FontStyle.italic,
      color: primaryTextColor,
    ),
    titleLarge: GoogleFonts.inter(
      fontSize: 18,
      fontWeight: FontWeight.w700,
      fontStyle: FontStyle.italic,
      color: primaryTextColor,
    ),
    titleMedium: GoogleFonts.inter(
      fontSize: 16,
      fontWeight: FontWeight.w600,
      color: primaryTextColor,
    ),
    titleSmall: GoogleFonts.inter(
      fontSize: 14,
      fontWeight: FontWeight.w600,
      color: primaryTextColor,
    ),
    // Body — regular weight per brand spec
    bodyLarge: GoogleFonts.inter(
      fontSize: 16,
      fontWeight: FontWeight.w400,
      color: primaryTextColor,
    ),
    bodyMedium: GoogleFonts.inter(
      fontSize: 14,
      fontWeight: FontWeight.w400,
      color: primaryTextColor,
    ),
    bodySmall: GoogleFonts.inter(
      fontSize: 12,
      fontWeight: FontWeight.w400,
      color: secondaryTextColor,
    ),
    labelLarge: GoogleFonts.inter(
      fontSize: 14,
      fontWeight: FontWeight.w600,
      color: primaryTextColor,
    ),
    labelMedium: GoogleFonts.inter(
      fontSize: 12,
      fontWeight: FontWeight.w500,
      color: secondaryTextColor,
    ),
    labelSmall: GoogleFonts.inter(
      fontSize: 11,
      fontWeight: FontWeight.w500,
      color: secondaryTextColor,
      letterSpacing: 0.05,
    ),
  );
}

// ── App Themes ────────────────────────────────────────────────────────────────
class AppTheme {
  AppTheme._();

  // Req 18.1, 18.6: Light mode — White surfaces, Dark Navy text, Primary Green primary
  static ThemeData get light => ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    scaffoldBackgroundColor: AppColors.lightSurface,
    colorScheme: const ColorScheme.light(
      primary: AppColors.primaryGreen,
      onPrimary: AppColors.white,
      secondary: AppColors.darkNavy,
      onSecondary: AppColors.white,
      surface: AppColors.lightSurface,
      onSurface: AppColors.darkNavy,
      error: AppColors.error,
      onError: AppColors.white,
    ),
    textTheme: _buildTextTheme(AppColors.darkNavy, const Color(0xFF4A5568)),
    appBarTheme: AppBarTheme(
      backgroundColor: AppColors.white,
      foregroundColor: AppColors.darkNavy,
      elevation: 0,
      centerTitle: true,
      iconTheme: const IconThemeData(color: AppColors.darkNavy),
      titleTextStyle: GoogleFonts.inter(
        fontSize: 17,
        fontWeight: FontWeight.w700,
        color: AppColors.darkNavy,
      ),
    ),
    cardTheme: CardThemeData(
      color: AppColors.white,
      elevation: 1,
      shadowColor: Colors.black12,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primaryGreen,
        foregroundColor: AppColors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: const Color(0xFFF7FAFC),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.primaryGreen, width: 2),
      ),
      hintStyle: GoogleFonts.inter(color: const Color(0xFFA0AEC0)),
      labelStyle: GoogleFonts.inter(color: const Color(0xFF718096)),
    ),
    dividerTheme: const DividerThemeData(color: Color(0xFFE2E8F0), thickness: 1),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: AppColors.white,
      selectedItemColor: AppColors.primaryGreen,
      unselectedItemColor: Color(0xFFA0AEC0),
      type: BottomNavigationBarType.fixed,
      elevation: 8,
    ),
  );

  // Req 18.1, 18.6: Dark mode — Dark Green surfaces, White text, Primary Green primary
  static ThemeData get dark => ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: AppColors.darkGreen,
    colorScheme: const ColorScheme.dark(
      primary: AppColors.primaryGreen,
      onPrimary: AppColors.white,
      secondary: AppColors.primaryGreen,
      onSecondary: AppColors.darkNavy,
      surface: Color(0xFF235C34),
      onSurface: AppColors.white,
      error: AppColors.error,
      onError: AppColors.white,
    ),
    textTheme: _buildTextTheme(AppColors.white, const Color(0xFFCBD5E0)),
    appBarTheme: AppBarTheme(
      backgroundColor: AppColors.darkGreen,
      foregroundColor: AppColors.white,
      elevation: 0,
      centerTitle: true,
      iconTheme: const IconThemeData(color: AppColors.white),
      titleTextStyle: GoogleFonts.inter(
        fontSize: 17,
        fontWeight: FontWeight.w700,
        color: AppColors.white,
      ),
    ),
    cardTheme: CardThemeData(
      color: const Color(0xFF235C34),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: Color(0x33FFFFFF)),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primaryGreen,
        foregroundColor: AppColors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: const Color(0xFF235C34),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0x33FFFFFF)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0x33FFFFFF)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.primaryGreen, width: 2),
      ),
      hintStyle: GoogleFonts.inter(color: const Color(0xFF9DC4A8)),
      labelStyle: GoogleFonts.inter(color: const Color(0xFFB8D9C0)),
    ),
    dividerTheme: const DividerThemeData(color: Color(0x33FFFFFF), thickness: 1),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: AppColors.darkGreen,
      selectedItemColor: AppColors.primaryGreen,
      unselectedItemColor: Color(0xFF9DC4A8),
      type: BottomNavigationBarType.fixed,
      elevation: 8,
    ),
  );
}

// ── Reusable Widgets ──────────────────────────────────────────────────────────
