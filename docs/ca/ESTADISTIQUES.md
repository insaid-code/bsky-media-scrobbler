# 📊 Motor d'Estadístiques, Informes i Collages Visuals

`bsky-media-scrobbler` inclou un complet motor analític que analitza els teus hàbits de consum multimèdia, calcula balanços temporals tancats, munta collages visuals en alta definició i celebra fites al teu perfil de Bluesky.

---

## 🗓️ Calendari de Publicacions Periòdiques

| Informe | Moment de Publicació | Període Analitzat | Format i Contingut |
| :--- | :--- | :--- | :--- |
| **Balanç Setmanal** | **Dilluns a les 09:30h** *(o posterior)* | Setmana natural completa tancada (Dilluns 00:00 a Diumenge 23:59:59) | Collage de caràtules (**3x3** o **2x2**), episodis vistos, minuts i hores totals, pel·lícules i sèries finalitzades. |
| **Balanç Mensual** | **Dia 1 de mes a les 09:30h** *(o posterior)* | Mes natural complet tancat (Dia 1 00:00 a fi de mes 23:59:59) | Collage visual, minuts totals, sèries completades i pel·lícules registrades durant el mes vençut. |
| **Curiositat / Fun Fact** | **Dia 15 de mes a les 12:00h** *(o posterior)* | Historial analític consolidat | Rotació de 3 curiositats: patró de dia/hora preferida de marató, sèrie més llarga completada (medalla a la fidelitat) o taxa de finalització. |
| **Ratxes de Dies Actius** | En sincronitzar activitat diària | Dies consecutius amb visionats | Celebració de ratxa en assolir **7 dies continus** i en increments setmanals (14, 21, 28, 35...). |
| **Fites Històriques** | En temps real després de completar fitxes | Comptador acumulat global | Celebració en creuar marques rodones (ex. 18.000 episodis, 400 sèries acabades, 450 pel·lícules). |

---

## 🖼️ Generació de Collages amb Pillow

El motor genera automàticament imatges compostes optimitzades per a Bluesky (`collage.py`):

1. **Quadrícula 3x3 (Per defecte):**
   * Mostra fins a **9 caràtules** en format pòster vertical (proporció estàndard 2:3).
   * Mida final: **1200 x 1800 px** en format JPEG d'alta qualitat amb compressió adaptativa `< 950 KB` (respectant els límits de pujada de Bluesky).
   * Selecció intel·ligent: Prioritza caràtules de sèries diferents i pel·lícules vistes durant la setmana o el mes. Si el catàleg és inferior a 9 però superior a 3, commuta automàticament a 2x2.
2. **Quadrícula 2x2:**
   * Mostra **4 caràtules** principals.
   * Mida final: **1200 x 1800 px**.
   * Ideal per a setmanes amb menys varietat de títols o maratons centrades en poques sèries.

---

## ⚡ Disparadors Manuals sota Demanda (`Triggers`)

No cal esperar al dilluns o al dia 1 per provar o previsualitzar un balanç. El bucle de `app/main.py` comprova cada 5 segons la presència de fitxers senyal a `/data`:

### 1. Forçar Resum Setmanal
```bash
# Quadrícula estàndard 3x3
echo "3x3" > data/trigger_weekly

# O quadrícula compacta 2x2
echo "2x2" > data/trigger_weekly
```

### 2. Forçar Resum Mensual
```bash
# Quadrícula estàndard 3x3
echo "3x3" > data/trigger_monthly

# O quadrícula compacta 2x2
echo "2x2" > data/trigger_monthly
```

### 3. Forçar Curiositat / Fun Fact
```bash
touch data/trigger_fun_fact
```

> **Comportament automàtic:** Tan bon punt el contenidor detecta el fitxer senyal, executa la tasca immediatament, genera l'informe amb la seva imatge, el publica a Bluesky i elimina el fitxer per evitar re-execucions. També pots crear-los mitjançant Docker: `docker exec bsky-media-scrobbler touch /data/trigger_fun_fact`.

---

## 🎛️ Integració amb Taulers de Control (OliveTin / HomeLab)

Si disposes d'un tauler d'accions web com **OliveTin**, pots afegir botons directes al teu fitxer `config.yaml` per disparar aquestes funcions amb un sol toc:

```yaml
  # --- BLUESKY MEDIA SCROBBLER ---
  - title: "🦋 Bluesky: Forçar Resum Mensual"
    icon: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='24' height='24'><path fill='#1185fe' d='M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566 1.018 1.561 1.748 1.561 3.254c0 3.28 1.83 13.435 8.439 13.435 3.398 0 4.887-2.98 5.86-5.889z'/></svg>"
    shell: "echo '{{ grid }}' > /ruta/a/bsky-media-scrobbler/data/trigger_monthly && echo 'Disparador mensual enviat amb collage {{ grid }}'"
    timeout: 30
    arguments:
      - name: grid
        title: "Tipus de Quadrícula"
        choices:
          - title: "🎨 Quadrícula 3x3 (9 caràtules)"
            value: "3x3"
          - title: "🖼️ Quadrícula 2x2 (4 caràtules)"
            value: "2x2"

  - title: "🦋 Bluesky: Forçar Curiositat / Fun Fact"
    icon: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='24' height='24'><path fill='#f59e0b' d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z'/></svg>"
    shell: "touch /ruta/a/bsky-media-scrobbler/data/trigger_fun_fact && echo 'Petició de Curiositat / Fun Fact enviada al scrobbler.'"
    timeout: 15
```
