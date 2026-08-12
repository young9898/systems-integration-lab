FROM httpd:2.4-alpine
COPY index.html /usr/local/apache2/htdocs/index.html
# COPY preserves the HOST file's permission bits. If the checkout has restrictive
# modes — iCloud Drive creates files 0600, and some umask settings do the same —
# the file lands in the image unreadable by Apache, which runs as www-data. The
# symptom is a 403 with "file permissions deny server access" in the error log,
# which reads like a config problem and is not one. Normalise it here so the
# build does not depend on the permissions of the machine that ran it.
RUN chmod 644 /usr/local/apache2/htdocs/index.html
