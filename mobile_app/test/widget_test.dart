import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/main.dart';

void main() {
  testWidgets('BiometricFieldApp smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const BiometricFieldApp());
    expect(find.byType(BiometricFieldApp), findsOneWidget);
  });
}
