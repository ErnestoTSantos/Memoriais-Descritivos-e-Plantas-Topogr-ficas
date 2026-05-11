# Casos de teste - Irradiacao

Use a modalidade `Irradiacao` com estacao:

- `Estacao X`: `500000.00`
- `Estacao Y`: `9000000.00`

## Caso valido (controle)

```txt
V-01, 0, 100
V-02, 90, 100
V-03, 180, 100
V-04, 270, 100
```

## Caso de erro 1 (azimute com prefixo textual)

Esperado: erro de azimute invalido no parser.

```txt
V-01, Az 90°00'00", 100
V-02, 180, 100
V-03, 270, 100
```

## Caso de erro 2 (distancia zerada)

Esperado: `A distancia da irradiacao deve ser maior que zero.`

```txt
V-01, 0, 120
V-02, 90, 0
V-03, 180, 90
```

## Caso de erro 3 (observacoes insuficientes)

Esperado: `Informe ao menos 3 observacoes de irradiacao para formar o poligono.`

```txt
V-01, 0, 100
V-02, 90, 100
```
