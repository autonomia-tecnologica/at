# 8. Extensions and plugins [normative]

- The extension exists to teach AT, and the first of them is the slang map: it is data that changes by region, by person and by time, and waiting for a release to be understood is too expensive.

- **No extension executes code today.** The first class is **pure data**: a folder with a declaration and the data, with not one executable line. A data plugin has no runtime presence at all — it is not a process, not a reader: whoever reads the sentence is AT, and the plugin only says how to translate. That is why it does not ask for a read permission; asking would be theatre, and theatre teaches people to click "accept" without reading the next one.

- **The plugin carries a manifest**, and the manifest declares what it does in the environment. The permissions are granular and the person sees what they are installing. The first permission in AT's history is about what the plugin **alters**: *"Esse plugin pode alterar suas palavras antes de ser analisado pelo motor (core) do AT."* The sentence of the permission belongs to the **product**, rendered from the internal name in the product's `i18n` — the plugin merely references the id, because a warning written by whoever is being warned is not a warning. The plugin may add a note of authorship, marked as its own.

- **Installing ties a review to a hash.** AT sees what exists on disk and keeps the state; copying into the folder makes it **see**, and the act of installing is what counts. The plugin's whole folder is hashed, **content only, in canonical order** — no modification time, no permission, no empty folder —, and any altered byte changes the hash, invalidates the review and lowers the grade. The acceptances have to be made again, which closes the classic hole of trusting the author: the thing you approved and the thing that runs afterwards are the same, or AT knows they are not.

- The way back up the grade is an **explicit review**, in one of three modes: *I read what it does*, *I asked an AI to read what it does*, *I trust whoever made it*. Nobody verifies the declaration — it is the only possible format — and that is why the grade presents itself as a declaration (§3, The security posture).

- The plugin state lives in `app/`, in a file, and not in the tables. Since the folder is the person's, one can edit that state and lie to one's own grade: that is not a flaw in the design, because the hash protects you **from the author**, not the author from you.

- **Code is the last option.** Code that executes is code that is hard to contain, and before it the plan is to deliver extension in much more established forms.
