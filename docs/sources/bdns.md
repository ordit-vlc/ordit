# Fil BDNS — Base de Datos Nacional de Subvenciones

Spike de la Fase 5 (eix "capital de fora"). La BDNS publica **totes** les subvencions
públiques espanyoles a nivell d'entitat, amb API JSON oberta. El descobriment clau: cada
concessió porta el **NIF/CIF del beneficiari**, cosa que FEGA no porta. És l'eix natural per
a guanyar identificador fort i, més avant, el backbone d'entitat canònica (Fase 6).

## Procedència i llicència

| Camp | Valor |
|------|-------|
| Organisme | IGAE — Intervención General de la Administración del Estado (Ministeri d'Hisenda) |
| Sistema | SNPSAP / BDNS (Sistema Nacional de Publicidad de Subvenciones y Ayudas Públicas) |
| Portal (URL) | https://www.pap.hacienda.gob.es/bdnstrans/GE/es/concesiones |
| API base (URL) | `https://www.infosubvenciones.es/bdnstrans/api` |
| Endpoint usat | `/concesiones/busqueda` (GET, JSON) |
| Endpoint auxiliar | `/regiones` (arbre NUTS; la Comunitat Valenciana ES52 té `id=54`) |
| Llicència | Dades obertes de reutilització (Llei 37/2007 i Llei 19/2013 de transparència); reutilització lliure amb atribució, compatible amb CC-BY-4.0 |
| Data de descàrrega | 2026-06-23 (slice CV 2023, 8.830 concessions) |

## Cadència

Actualització **diària** a la BDNS. Les dades de concessions són històriques i estables una
vegada publicades. L'API filtra per rang de dates (`fechaDesde`/`fechaHasta`, format
`DD/MM/YYYY`) i per regió d'impacte (`regiones`). Límit de 10.000 registres per pàgina;
`ingest/bdns/download.py` pagina amb `pageSize=1000` fins esgotar `totalPages`.

## Reproduir la descàrrega

```
uv run python -m ingest.bdns.download   # baixa CV 2022-2024 a data/raw/bdns/ (gitignored)
```

El raw (`data/raw/bdns/concesiones_cv_<any>.jsonl`, una concessió per línia) és **gitignored**:
mai a git ni a CI (CLAUDE.md §8). CI valida contra la fixture sintètica
`tests/fixtures/bdns_raw/concesiones_cv_sample.jsonl` (entitats fictícies).

## Esquema real (camps de la font, endpoint /concesiones/busqueda)

Noms de camp tal com els publica la font (castellà camelCase: és procedència). El contracte
`contracts/bdns.py` els mapeja a identificadors interns en anglés (capa ordit).

| Camp font | Tipus | Nullable | Descripció |
|-----------|-------|----------|------------|
| `id` | int | no | Identificador intern de la concessió |
| `codConcesion` | str | no | Codi de concessió (p. ex. `SB117197181`, `GR...`) |
| `fechaConcesion` | str | no | Data de concessió `YYYY-MM-DD` |
| `beneficiario` | str | no | **`<NIF/CIF> <NOM>`** (vegeu la pregunta crítica) o codi `ZZ...Z` |
| `instrumento` | str | no | Instrument (SUBVENCIÓN, GARANTÍA, PRÉSTAMO...) |
| `importe` | float/int | no | Import concedit (EUR) |
| `ayudaEquivalente` | float/int | no | Ajuda equivalent (EUR; difereix d'`importe` en préstecs/garanties) |
| `urlBR` | str | no* | URL del butlletí/resolució (BR) |
| `tieneProyecto` | bool | no | Si té projecte associat |
| `numeroConvocatoria` | str | no* | Número de convocatòria |
| `idConvocatoria` | int | no* | Id de la convocatòria |
| `convocatoria` | str | no* | Títol de la convocatòria (castellà) |
| `descripcionCooficial` | str | **sí** | Títol cooficial (valencià); ~36% null al slice |
| `nivel1` | str | no | Nivell administratiu (AUTONOMICA / LOCAL / ESTATAL...) |
| `nivel2` | str | no | Administració (p. ex. COMUNITAT VALENCIANA) |
| `nivel3` | str | **sí** | Òrgan concedent (~0,5% null) |
| `codigoInvente` | str | **sí** | Codi INVENTE (~75% null) |
| `idPersona` | int | no | Id intern del beneficiari a la BDNS |
| `fechaAlta` | str | no* | Data d'alta del registre |

(*) No observats null al slice CV 2023, però es modelen com a opcionals per prudència.

A nivell de resposta (no de registre): `content` (array), `totalElements`, `totalPages`,
`number`, `size`, i un camp `advertencia` amb l'avís legal de la font.

## Pregunta crítica de l'spike: el CIF és utilitzable? → **SÍ (GO)**

El camp `beneficiario` incrusta el **NIF/CIF al principi**, separat del nom per un espai:
`"B67649640 CAMINO AL ENSANCHE SL"`, `"P1210600A AYUNTAMIENTO DE SONEJA"`. El contracte
l'extrau amb una regex de 9 alfanumèrics inicials (`BdnsConcesion.nif_cif`).

Mesurat sobre el slice real **CV 2023 (8.830 concessions, 2.095 M€)**:

- **8.830 / 8.830 (100%)** porten un identificador de 9 caràcters extraïble. **0 fallits** de
  validació del contracte.
- **8.808 (99,75%)** són **persones jurídiques o ens públics** (CIF amb lletra inicial
  A-W), que representen **99,99% dels euros**. Clau forta directament utilitzable.
- **21** són codis **`ZZ...Z`**: entitats sense NIF estàndard (p. ex. cases regionals
  valencianes a l'estranger), no persones físiques. `is_legal_person=False`.
- **1** és un **NIE** (`Z0035412C`, el nom n'és el mateix NIE, sense raó social): l'únic
  registre que podria ser persona física, i ve **en clar, no emmascarat**. `is_legal_person=False`.

### Evidència crua (caracterització del `*` i de les persones físiques)

Esta secció fixa una conclusió que durant l'anàlisi inicial es va llegir malament (primer es
va comptar el `*` com a emmascarament, ~2,5%) i que cal deixar provada amb dades crues.

**El `*` és un artefacte del NOM, no una anonimització de l'identificador.** Dels 8.830
registres, **223 (2,5%) porten `*`**, i en **0** el `*` està dins de l'identificador: 202 són
un `*` final del nom i 21 interior, sempre sobre un CIF de persona jurídica vàlid:

```
'Q1200275D IES LA PLANA *'
'P0301800I AYUNTAMIENTO DE ALTEA *'
'B67958439 COSMIC * SPELLS.L'
'J42512798 DUENDES * SC'
'P0309100F AYTO. * MURLA'
```

**No hi ha persones físiques present-però-emmascarades.** La distribució de la lletra inicial
de l'identificador (8.830 registres) ho tanca:

```
P 2594  G 2284  B 2070  R 624  Q 578  F 283  A 195  V 95
E 25    J 25    Z 22    S 21   U 6    W 5    N 2    H 1
```

- **0 identificadors comencen per dígit** → cap **DNI** (persona física espanyola = 8 dígits
  + lletra, comença per dígit).
- Les lletres A-W són, **per llei, prefixos de persona jurídica / ens públic** (Ordre
  EHA/451/2008 i normativa del NIF). Una física mai porta un CIF amb eixes lletres, així que
  **cap dels 8.808 "jurídics" pot ser una física dissimulada**: la xifra és exacta per
  construcció, no per heurística.
- L'única lletra "de física" present és `Z` (22 casos): 21 són el placeholder `ZZ...Z` i només
  **1 és un NIE real**, en clar.

**Contrast amb la norma del BDNS.** El BDNS **sí que publica** persones físiques (RD 130/2019;
Ley 38/2003, art. 18 i 20), amb garanties de privacitat i excloent del registre els casos de
protecció especial. Quan apareixen, ho fan amb el seu NIF (DNI/NIE), no amb un CIF. Per tant,
la quasi-absència de físiques en este tall **no és ocultació ni mala classificació**: és que
les subvencions de la CV de 2023 recollides ací van quasi totes a entitats i ens públics. Si
un tall futur en porta, apareixeran com a DNI (dígit inicial) o NIE (X/Y/Z) — mai sota una
lletra de CIF—, així que el recompte de jurídiques-amb-CIF es manté fiable.

Conclusió: **GO**. El CIF és present i utilitzable per a la pràctica totalitat dels euros, el
que habilita la ingesta (Fase 5b) i el backbone d'entitat canònica per CIF (Fase 6). La
caracterització original (el `*` és artefacte de nom; ~0 persones físiques) queda
**confirmada amb evidència**, amb la correcció de "22 ZZ" a "21 ZZ + 1 NIE".

## Peculiaritats conegudes

- **NIF/CIF incrustat al nom**: cal separar-lo (primer token de 9 caràcters); la resta és el
  nom. Staging (Fase 5b) farà esta separació en SQL.
- **Codis `ZZ...Z`**: placeholder per a entitats sense NIF estàndard; no són clau forta.
- **Artefacte `*` al nom**: 223 registres (2,5%) duen un `*` final o intern **al nom** (p. ex.
  `"... AYUNTAMIENTO DE ALTEA *"`); a netejar al nom. **Mai apareix dins de l'identificador**,
  així que no és cap anonimització del NIF/CIF (vegeu l'evidència crua de dalt).
- **`importe` vs `ayudaEquivalente`**: en garanties i préstecs difereixen (l'equivalent és el
  subsidi real); cal decidir quina mesura es publica al mart.
- **Persones físiques**: el BDNS les publica amb el seu NIF (DNI dígit-inicial, o NIE X/Y/Z),
  no sota lletra de CIF; els casos de protecció especial no es registren (RD 130/2019). En este
  tall CV 2023 en són ~0 (només 1 NIE en clar): no estan emmascarades dins dels CIF. Mode
  privat (CLAUDE.md §8): no afegim ni desfem cap anonimització.
- **Mode privat**: el raw es manté sencer i local; res no es publica.
