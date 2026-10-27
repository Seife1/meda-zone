import 'package:flutter/material.dart';

/// Reusable AppBar showing the MedaZone logo image.
/// Uses logo_dark.png on light surfaces and logo_light.png on dark surfaces.
class BrandAppBar extends StatelessWidget implements PreferredSizeWidget {
  const BrandAppBar({
    super.key,
    this.actions,
    this.leading,
    this.bottom,
  });

  final List<Widget>? actions;
  final Widget? leading;
  final PreferredSizeWidget? bottom;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final logoAsset = isDark
        ? 'assets/images/logo_light.png'
        : 'assets/images/logo_dark.png';

    return AppBar(
      leading: leading,
      centerTitle: true,
      actions: actions,
      bottom: bottom,
      title: Image.asset(
        logoAsset,
        height: 32,
        fit: BoxFit.contain,
      ),
      backgroundColor: Theme.of(context).appBarTheme.backgroundColor,
      elevation: 0,
    );
  }

  @override
  Size get preferredSize => Size.fromHeight(
        kToolbarHeight + (bottom?.preferredSize.height ?? 0.0),
      );
}
