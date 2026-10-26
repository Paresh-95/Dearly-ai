const REVERSE_RELATIONS: Record<string, string> = {
  mother: "son/daughter",
  mom: "son/daughter",
  father: "son/daughter",
  dad: "son/daughter",
  parent: "child",
  grandmother: "grandson/granddaughter",
  grandma: "grandson/granddaughter",
  grandfather: "grandson/granddaughter",
  grandpa: "grandson/granddaughter",
  grandparent: "grandchild",
  sister: "brother/sister",
  brother: "brother/sister",
  sibling: "sibling",
  wife: "husband",
  husband: "wife",
  spouse: "spouse",
  partner: "partner",
  aunt: "niece/nephew",
  uncle: "niece/nephew",
  niece: "aunt/uncle",
  nephew: "aunt/uncle",
  cousin: "cousin",
  daughter: "mother/father",
  son: "mother/father",
  child: "parent",
  "best friend": "best friend",
  friend: "friend",
  "college friend": "college friend",
  "childhood friend": "childhood friend",
  "close friend": "close friend",
  mentor: "mentee",
  mentee: "mentor",
  teacher: "student",
  student: "teacher",
  boss: "employee",
  manager: "employee",
  employee: "manager",
  colleague: "colleague",
  coworker: "coworker",
  neighbor: "neighbor",
  "mother-in-law": "daughter-in-law/son-in-law",
  "father-in-law": "daughter-in-law/son-in-law",
  "daughter-in-law": "mother-in-law/father-in-law",
  "son-in-law": "mother-in-law/father-in-law",
};

const POSSESSIVE_PREFIX_RE = /^(my|their|his|her|our)\s+/i;

/** Best-effort guess at the reverse of a relationship term — "grandmother"
 * -> "grandson/granddaughter" — for auto-filling the other side of a
 * relationship pair. Free-text input can't be mapped exhaustively, so an
 * unrecognized term returns "" and leaves the field for the user to fill
 * in themselves rather than guessing wrong.
 */
export function inferReverseRelation(relation: string): string {
  const normalized = relation.trim().toLowerCase().replace(POSSESSIVE_PREFIX_RE, "");
  return REVERSE_RELATIONS[normalized] ?? "";
}
