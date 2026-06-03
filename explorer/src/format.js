/* Formatadors uniformes de tot l'explorador (taula, llistat, mapa, focus, desglossament,
   totals). Una sola font per a cada unitat: milers "." i decimal "," (locale ca-ES). Cap
   arrodoniment ad hoc fora d'aci; cap valor numeric sense els seus decimals fixos.

   - fmtInt   : comptes sencers (beneficiaris, files, municipis).
   - fmtEur   : euros, SEMPRE enters, sense centims, amb separador de milers.
   - fmtHa    : hectarees, SEMPRE 1 decimal (108,0 · 1.313,3).
   - fmtEurHa : euros per hectarea, SEMPRE 1 decimal fix. */

const intFmt = new Intl.NumberFormat("ca-ES", { maximumFractionDigits: 0 });
const ha1 = new Intl.NumberFormat("ca-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const fmtInt = (n) => intFmt.format(n);
export const fmtEur = (n) => intFmt.format(Math.round(n)) + " €";
export const fmtHa = (n) => ha1.format(n) + " ha";
export const fmtEurHa = (n) => ha1.format(n) + " €/ha";
