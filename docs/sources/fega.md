# Fil: FEGA — beneficiaris de la PAC (FEAGA/FEADER)

Transparència de beneficiaris d'ajudes de la PAC publicada pel FEGA (Fons Espanyol de
Garantia Agrària), en compliment del Reglament (UE) 2021/2116.

## Procedència

| Camp | Valor |
|------|-------|
| Organisme | FEGA — Fons Espanyol de Garantia Agrària (MAPA) |
| Portal (URL) | https://www.fega.gob.es/es/datos-abiertos/consulta-de-beneficiarios-pac |
| URL de la pàgina de descàrrega | https://www.fega.gob.es/es/datos-abiertos/consulta-de-beneficiarios-pac/descarga-de-ficheros |
| URL directa del fitxer (exercici 2024) | https://www.fega.gob.es/sites/default/files/files/document/Beneficiarios_municipio_ejercicio-financiero-2024.zip |
| Exercici financer | 2024 (16 oct 2023 – 15 oct 2024) |
| Data de descàrrega | 2026-06-02 |
| `Last-Modified` del fitxer | 2025-06-23 |
| Llicència | Dades obertes del FEGA; reutilització amb atribució (compatible amb CC-BY-4.0) |
| Cadència | Anual. Cada exercici es publica i es manté consultable **2 anys** des de la publicació inicial (Reg. UE 2021/2116). En el moment de la descàrrega hi havia 2024 i 2025 per municipi. |

## Format

- **Contenidor**: ZIP (33,8 MiB) amb **un sol fitxer** `.txt`,
  `Beneficiarios_municipio_ejercicio_financiero_2024.txt` (296 MiB descomprimit).
- **Codificació**: **ISO-8859-1 (latin-1)**, NO UTF-8. Sense BOM.
- **Final de línia**: CRLF.
- **Delimitador**: punt i coma `;`. **Cada línia acaba en `;`** → 14 camps per `awk`
  (13 columnes reals + un camp buit final).
- **Separador decimal**: coma (`,`), format espanyol, **sense punt de milers**
  (p. ex. `24217,98`).
- **Abast**: **nacional** (totes les CCAA). El filtre a la Comunitat Valenciana es fa en
  procés, no en la baixada. La CV apareix amb etiqueta bilingüe a `PROVINCIA`:
  `València/Valencia`, `Castelló/Castellón`, `Alacant/Alicante`.
- **Volum**: 2.217.850 files de dades (capçalera inclosa a banda). ~146.539 files de la CV.

## Esquema real (capçalera del fitxer)

```
BENEFICIARIO;GRUPO_EMPRESA;PROVINCIA;MUNICIPIO;MEDIDA;OBJETIVO_ESP;FEC_INI;FEC_FIN;FEAGA;FEADER;IMPORTECOFIN;FEADER_COFIN;IMPORTE_EUROS
```

| # | Columna | Descripció | Notes |
|---|---------|------------|-------|
| 1 | `BENEFICIARIO` | Raó social, nom de persona física, o **codi anònim** | Vegeu anonimització |
| 2 | `GRUPO_EMPRESA` | Grup/holding al qual pertany, com a `CIF-NOM` | Sovint buit. **Únic lloc amb identificador fiscal**, i només del grup |
| 3 | `PROVINCIA` | Província | Etiqueta bilingüe a la CV |
| 4 | `MUNICIPIO` | `CODI_INE - Nom` (p. ex. `46147 - Casas Altas`) | Emmascarat si és xicotet (vegeu avall) |
| 5 | `MEDIDA` | Mesura/intervenció (p. ex. `I.1   Ayuda básica a la renta...`) | Codi + descripció en un sol camp, separats per espais |
| 6 | `OBJETIVO_ESP` | Objectiu(s) específic(s) | **Multivalor separat per `\|`** (p. ex. `OE4\|OE5\|OE6\|OE9`); sovint buit |
| 7 | `FEC_INI` | Data d'inici (operacions plurianuals) | `DD/MM/YYYY`; sovint buit |
| 8 | `FEC_FIN` | Data fi | `DD/MM/YYYY`; sovint buit |
| 9 | `FEAGA` | Import FEAGA (€) | Coma decimal. >0 en 1.983.904 files |
| 10 | `FEADER` | Import FEADER (€) | Coma decimal. >0 en 218.225 files |
| 11 | `IMPORTECOFIN` | Cofinançament | Coma decimal |
| 12 | `FEADER_COFIN` | Cofinançament FEADER | Coma decimal |
| 13 | `IMPORTE_EUROS` | Import total de la línia (€) | Coma decimal |

Cada fila és **una línia per mesura** d'un beneficiari, no un beneficiari agregat.

## Peculiaritats conegudes

- **No hi ha columna `NIF`/`CIF` del beneficiari.** L'únic identificador fiscal és el del
  **grup** a `GRUPO_EMPRESA` (`CIF-NOM`), i només quan el beneficiari pertany a un grup.
- **No hi ha columna `ejercicio`**: l'exercici només viu al **nom del fitxer**; s'ha
  d'injectar en la ingesta.
- **No hi ha columna `fondo`**: el fons s'infereix de quina columna d'import està
  poblada (`FEAGA` vs `FEADER`); una fila pot tindre tots dos a 0 si l'import va per
  cofinançament.
- **No hi ha `comarca_agraria`** en el fitxer "per municipi". L'agregació de municipis
  xicotets es fa **emmascarant** el municipi com `PPXXX - XXXXX` (es manté el codi de
  província `PP`, la resta a `X`), no anomenant la comarca. (Hi ha consultes interactives
  i, possiblement, un fitxer "per comarca" a banda, no descarregat ací.)
- **Anonimització de persones físiques** (Reg. UE 2021/2116, ≤ 1.250 €): el nom es
  reemplaça per un codi `ES#NNNNNNNN` a `BENEFICIARIO` i el municipi s'emmascara a
  `PPXXX - XXXXX`. ~4.480 files nacionals / 763 de la CV. **Les persones físiques que
  cobren > 1.250 € SÍ apareixen amb nom i cognoms reals** (dada personal): el fitxer
  **no porta cap marca** que les separe de les persones jurídiques —cal classificació per
  nom o enllaç extern (BORME, Fase 3)—, cosa crítica per a la regla RGPD d'Ordit (només
  persones jurídiques publicades).
- **Files malformades**: ~2 línies amb un `;` incrustat al nom desplacen els camps
  (apareix una "província" `SL`). Cal una regla de sanejament a staging.

## Estat del contracte

El contracte provisional inicial **no casava** amb este esquema (sense `NIF`, sense
`ejercicio`, sense `fondo` únic, sense `comarca_agraria`; imports en coma decimal). El
go/no-go de la Fase 0 queda **tancat**: `contracts/fega.py` s'ha **reescrit** contra el
fitxer real (imports en `Decimal`, `financial_year` injectat des del nom de fitxer,
`amount_feaga`/`amount_feader` separats, `GRUPO_EMPRESA` cru). La validació es prova amb
una fixture sintètica de persones jurídiques a `tests/fixtures/fega_sample.csv` (cap dada
de persona física al repo). La partició de `GRUPO_EMPRESA` i el filtre juridica/fisica
pertanyen a la Fase 1 (staging i marts), no al contracte.

## Reproduir la descàrrega

```sh
uv run python -m ingest.fega.download
```

Desa el ZIP a `data/raw/fega/` (gitignored: conté persones físiques, no es committeja mai).
