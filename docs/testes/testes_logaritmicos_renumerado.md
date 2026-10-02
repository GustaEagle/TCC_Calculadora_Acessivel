# Lista de Cálculos Logarítmicos com Resultados Esperados

## Logaritmos Básicos

1. `log10(100) = 2` - ✅
2. `log10(1000) = 3` - ✅
3. `log2(8) = 3` - ✅
4. `log2(1024) = 10` - ✅
5. `log5(125) = 3` - ✅
6. `log3(81) = 4` - ✅
7. `ln(e) = 1` - ✅
8. `ln(e^5) = 5` - ✅
9. `log10(0.1) = -1` - ✅
10. `log2(0.5) = -1` - ✅

\---

## Mudança de Base

11. `log4(64) = 3` - ✅
12. `log7(49) = 2` - ✅
13. `log9(27) = 1.5` - ✅
14. `log16(2) = 0.25` - ✅
15. `log25(5) = 0.5` - ✅

\---

## Propriedades dos Logaritmos

16. `log(10 \* 100) = 3` - ✅
17. `log(1000 / 10) = 2` - ✅
18. `log(10^5) = 5` - ✅
19. `log(2^8) ≈ 2.40824` - ✅
20. `log(50) + log(2) = 2` - ✅
21. `log(100) - log(10) = 1` - ✅
22. `2 \* log(10) = 2` - ✅
23. `log(sqrt(100)) = 1` - ✅

\---

## Casos com Resultado Decimal

24. `log10(7) ≈ 0.84510` - ✅
25. `log2(3) ≈ 1.58496` - ✅
26. `ln(2) ≈ 0.69315` - ✅
27. `log5(12) ≈ 1.54396` - ✅
28. `log7(100) ≈ 2.36658` - ✅

\---

## Casos Extremos / Validação

29. `log10(1) = 0` - ✅
30. `ln(1) = 0` - ✅
31. `log2(1) = 0` - ✅
32. `log10(0) -> erro esperado` - ✅
33. `log10(-5) -> erro esperado` - ✅
34. `log1(10) -> base inválida` - ✅
35. `log-2(8) -> base inválida` - ✅

\---

## Combinações Avançadas

36. `log2(32) + log2(4) = 7` - ✅
37. `log10(1000) - log10(10) = 2` - ✅
38. `log(1000) / log(10) = 3` - ✅
39. `ln(e^8) - ln(e^3) = 5` - ✅
40. `log3(27 \* 9) = 5` - ✅

\---

## Testes de Precisão

41. `ln(1.0001) ≈ 9.9999500033*10^-5` - ✅
42. `log10(999999) ≈ 5.999999566` - ✅
43. `log2(2048) = 11` - ✅
44. `log10(3.14159265) ≈ 0.4971498722` - ✅
45. `ln(123456789) ≈ 18.63140177` - ✅

\---

## Testes Mistos

46. `sqrt(log10(10000)) = 2` - ✅
47. `(log2(64))^2 = 36` - ✅
48. `log10(10^8) = 8` - ✅
49. `ln(sqrt(e^6)) = 3` - ✅
50. `log5(625) * 2 = 8` - ✅

\---

## Casos para Performance

51. `log2(2^100) = 100` - ✅
52. `ln(e^50) = 50` - ✅
53. `log10(10^20) = 20` - ✅
54. `log3(3^15) = 15` - ✅
55. `log7(7^30) = 30` - ✅

