# Glossary [normative]

Each name has one meaning, and names that would touch each other do not coexist. Whenever I invent a term, it is defined here before being used.

| term | what it is |
|---|---|
| **product** | the published set: this repository, the binary it generates and the declarations that travel inside |
| **binary** | the single file the product publishes |
| **Working Folder** | the folder where the binary was opened and which becomes its own |
| **layer** | each code folder with a single job: `core`, `data`, `prose`, `services`, `encryption`, `nlu`, `posture`, `ui`, `i18n` |
| **surface** | each way for a person to reach the core: `cli`, WebApp and Wizard |
| **service** | the capability, with a canonical name (`spelling-checker`, `identity-provider`) |
| **tool** | whoever fulfils the service today (LanguageTool, Authelia), replaceable without renaming anything |
| **table**, **schema**, **row**, **field** | the pieces of the data engine |
| **hashed field** | a field that stores the derivation and never the value; it is only compared |
| **instant field** | a field of a point in time: ISO, always UTC, with milliseconds |
| **day field** | a field of a calendar day, with no time and no timezone, local on write |
| **actor** | the row of `actor` that acts; **person**, **engine** and **agent** are the types |
| **access ceiling** | the effective limit of the actor; **role** is the row that grants it |
| **audit** | the `audit` table, the log of acts |
| **via** | where the act came in from: `cli`, WebApp, Wizard, `nlu`, engine. Port is the network one, and only that |
| **nlu** | the layer; **interpreter**, whoever does the work inside it; **vocabulary**, the per-language dictionary it consults |
| **interpreter test** | the ruler: what must work, what must be refused, what must be asked back |
| **risk threshold** | the price from which a demand waits for approval; below it, it runs |
| **demand risk** | the price of a demand, measured by the core over the action and the arguments |
| **permission catalogue** | the closed list `object:action` |
| **posture** | the measured security state of the environment: the graded functions and the grade |
| **grade** | the letter of a graded function, from `F` to `S`; the environment's is the weakest link |
| **functionality** | a capability the person recognizes, with levels and dependencies |
| **plugin** / **extension** | what teaches Bill something; today pure data only, with a manifest and a hash |
| **review** | the acceptance of a plugin, tied to the hash, in one of three modes |
| **Access Phrase** | what the person knows and types; from it the **Bill Key** is derived |
| **Bill Key** | the key derived from the Access Phrase; from it the **derived keys** derive, per service |
| **manifesto** | the seed of this repository, visible in the git history; and `manifest.json` is just the file that has that name |
| **pin**, **migration** | stay in English, like the rest of the code: version and hashing fixation, and the structure change that runs on the first start |
