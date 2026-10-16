const labels: Record<string, string> = {
  organization_name: "Organization name",
  organization_logo_token: "Organization logo",
  database: "Database configuration",
  "database.engine": "Database engine",
  "database.sqlite_path": "Database file",
  "database.host": "Database host",
  "database.port": "Database port",
  "database.database": "Database name",
  "database.username": "Database username",
  "database.password": "Database password",
  admin: "Administrator account",
  "admin.username": "Administrator username",
  "admin.email": "Administrator email",
  "admin.password": "Administrator password",
  "admin.first_name": "First name",
  "admin.last_name": "Last name",
  smtp: "SMTP configuration",
  "smtp.host": "SMTP host",
  "smtp.port": "SMTP port",
  "smtp.username": "SMTP username",
  "smtp.password": "SMTP password",
  "smtp.encryption": "SMTP encryption",
  "smtp.from_address": "SMTP sender email",
  "smtp.from_name": "SMTP sender name",
  recipient: "Test email recipient",
};

export function setupValidation(fields: Record<string, string[]>) {
  let step: number | undefined;
  const messages = Object.entries(fields).flatMap(([field, errors]) => {
    if (step === undefined) {
      if (field.startsWith("organization_")) step = 0;
      else if (field === "database" || field.startsWith("database.")) step = 1;
      else if (field === "admin" || field.startsWith("admin.") || field === "recipient") step = 2;
      else if (field === "smtp" || field.startsWith("smtp.")) step = 3;
    }
    return errors.map(
      (error) => `${labels[field] ?? field}: ${error.replace(/^Value error, /, "")}`,
    );
  });
  return { step, message: messages.join(" ") };
}
