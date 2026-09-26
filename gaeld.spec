Summary:	Swiss double-entry accounting, invoicing, and VAT
Name:		gaeld
Version:	3.8.25
Release:	1
License:	AGPL-3.0-or-later
Group:		System/Servers
URL:		https://gaeld.ch/
Source0:	https://github.com/Scanix/Gaeld/archive/refs/tags/v%{version}.tar.gz#/gaeld-%{version}.tar.gz
# composer install --no-dev --prefer-dist --optimize-autoloader
# plus bootstrap/cache from package:discover. No network at build time.
Source1:	gaeld-%{version}-vendor.tar.xz
# pnpm@11.20.0 install --frozen-lockfile && pnpm run build
Source2:	gaeld-%{version}-assets.tar.xz
Source3:	gaeld.env
Source4:	README.install.omv
BuildArch:	noarch
Requires:	php-cli
Requires:	php-bcmath
Requires:	php-ctype
Requires:	php-curl
Requires:	php-dom
Requires:	php-filter
Requires:	php-gd
Requires:	php-iconv
Requires:	php-intl
Requires:	php-mbstring
Requires:	php-openssl
Requires:	php-pcntl
Requires:	php-pdo
Requires:	php-pdo_pgsql
Requires:	php-pgsql
Requires:	php-phar
Requires:	php-posix
Requires:	php-redis
Requires:	php-session
Requires:	php-tokenizer
Requires:	php-xml
Requires:	php-xmlreader
Requires:	php-xmlwriter
Requires:	php-zip
Requires:	php-fpm
Requires:	gaeld-webserver-integration = %{EVRD}
Recommends:	postgresql
Recommends:	redis
Recommends:	tesseract
Requires(post):	%{_bindir}/runuser

%description
Gäld is a self-hosted double-entry accounting application for small
Swiss businesses. It covers the journal and ledger, Swiss QR-bill
invoicing, VAT, expenses, and CAMT bank reconciliation.

This package is the AGPL-3.0-or-later Community Edition. PostgreSQL
and Redis are expected on the local host. See README.install.omv
after installation.

%package nginx
Summary:	nginx and php-fpm integration for Gäld
Group:		System/Servers
Requires:	%{name} = %{EVRD}
Requires:	nginx
Requires:	php-fpm
Provides:	gaeld-webserver-integration = %{EVRD}

%description nginx
nginx site and php-fpm pool for Gäld. The site is installed disabled;
symlink it into sites-enabled and start php-fpm@gaeld.

%package apache
Summary:	Apache and php-fpm integration for Gäld
Group:		System/Servers
Requires:	%{name} = %{EVRD}
Requires:	apache-base
Requires:	apache-mod_proxy
Requires:	apache-mod_proxy_fcgi
Requires:	apache-mod_rewrite
Requires:	php-fpm
Provides:	gaeld-webserver-integration = %{EVRD}

%description apache
Apache snippet and php-fpm pool for Gäld. Point a virtual host at
/srv/www/gaeld/public and enable mod_proxy_fcgi.

%prep
%autosetup -p1 -n Gaeld-%{version}
tar -xf %{SOURCE1}
tar -xf %{SOURCE2}

%build

%install
cp %{SOURCE4} .
install -d %{buildroot}/srv/www/%{name}
cp -a . %{buildroot}/srv/www/%{name}/

rm -rf %{buildroot}/srv/www/%{name}/.git \
	%{buildroot}/srv/www/%{name}/.github \
	%{buildroot}/srv/www/%{name}/.githooks \
	%{buildroot}/srv/www/%{name}/.vscode \
	%{buildroot}/srv/www/%{name}/.specify \
	%{buildroot}/srv/www/%{name}/tests \
	%{buildroot}/srv/www/%{name}/scripts \
	%{buildroot}/srv/www/%{name}/node_modules
rm -rf %{buildroot}/srv/www/%{name}/docker
rm -f %{buildroot}/srv/www/%{name}/.env \
	%{buildroot}/srv/www/%{name}/.dockerignore \
	%{buildroot}/srv/www/%{name}/docker-compose.yml \
	%{buildroot}/srv/www/%{name}/compose.yaml \
	%{buildroot}/srv/www/%{name}/gaeld \
	%{buildroot}/srv/www/%{name}/phpunit.xml \
	%{buildroot}/srv/www/%{name}/phpunit.ee.xml \
	%{buildroot}/srv/www/%{name}/phpunit.xml.dist

find %{buildroot}/srv/www/%{name} -type d -exec chmod 0755 {} \;
find %{buildroot}/srv/www/%{name} -type f -exec chmod 0644 {} \;
chmod 0755 %{buildroot}/srv/www/%{name}/artisan

install -d %{buildroot}/srv/www/%{name}/storage/framework/cache/data
install -d %{buildroot}/srv/www/%{name}/storage/framework/sessions
install -d %{buildroot}/srv/www/%{name}/storage/framework/views
install -d %{buildroot}/srv/www/%{name}/storage/logs
install -d %{buildroot}/srv/www/%{name}/bootstrap/cache
install -d %{buildroot}/var/lib/%{name}/backups

install -d %{buildroot}%{_sysconfdir}/%{name}
install -m 0640 %{SOURCE3} %{buildroot}%{_sysconfdir}/%{name}/gaeld.env
ln -s %{_sysconfdir}/%{name}/gaeld.env %{buildroot}/srv/www/%{name}/.env

install -d %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/gaeld << 'EOF'
#!/bin/sh
cd /srv/www/gaeld || exit 1
exec /usr/bin/php artisan "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/gaeld

install -d %{buildroot}%{_sysconfdir}/php-fpm-instances.d
cat > %{buildroot}%{_sysconfdir}/php-fpm-instances.d/gaeld.conf << 'EOF'
[global]
error_log = syslog

[gaeld]
user = www
group = www
listen = /run/php-fpm/gaeld.sock
listen.owner = www
listen.group = www
listen.mode = 0660

pm = dynamic
pm.max_children = 20
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 5
pm.max_requests = 500

php_admin_value[memory_limit] = 512M
php_admin_value[upload_max_filesize] = 32M
php_admin_value[post_max_size] = 32M
php_admin_value[max_execution_time] = 120
php_admin_value[expose_php] = off
EOF

install -d %{buildroot}%{_sysconfdir}/nginx/sites-available
cat > %{buildroot}%{_sysconfdir}/nginx/sites-available/gaeld.conf << 'EOF'
upstream phpgaeld {
	server unix:/run/php-fpm/gaeld.sock;
}

server {
	listen 80;
	server_name gaeld.*;

	root /srv/www/gaeld/public;
	index index.php;

	client_max_body_size 32m;

	add_header X-Frame-Options "SAMEORIGIN";
	add_header X-Content-Type-Options "nosniff";

	location / {
		try_files $uri $uri/ /index.php?$query_string;
	}

	location = /favicon.ico { access_log off; log_not_found off; }
	location = /robots.txt  { access_log off; log_not_found off; }

	error_page 404 /index.php;

	location ~ \.php$ {
		fastcgi_pass phpgaeld;
		fastcgi_read_timeout 120;
		include fastcgi_params;
		fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
		fastcgi_param HTTPS $https if_not_empty;
	}

	location ~ /\.(?!well-known).* {
		deny all;
	}
}
EOF

install -d %{buildroot}%{_sysconfdir}/httpd/conf/webapps.d
cat > %{buildroot}%{_sysconfdir}/httpd/conf/webapps.d/gaeld.conf << 'EOF'
# Point a virtual host at /srv/www/gaeld/public and enable proxy_fcgi.
<Directory /srv/www/gaeld/public>
	AllowOverride None
	Require all granted
	DirectoryIndex index.php
	RewriteEngine On
	RewriteCond %{REQUEST_FILENAME} !-f
	RewriteCond %{REQUEST_FILENAME} !-d
	RewriteRule ^ index.php [L]
	<FilesMatch \.php$>
		SetHandler "proxy:unix:/run/php-fpm/gaeld.sock|fcgi://localhost"
	</FilesMatch>
</Directory>
EOF

install -d %{buildroot}%{_unitdir}
cat > %{buildroot}%{_unitdir}/gaeld-horizon.service << 'EOF'
[Unit]
Description=Gäld queue worker (Laravel Horizon)
After=network.target redis.service postgresql.service php-fpm@gaeld.service
Wants=redis.service

[Service]
User=www
Group=www
WorkingDirectory=/srv/www/gaeld
ExecStart=/usr/bin/php artisan horizon
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > %{buildroot}%{_unitdir}/gaeld-scheduler.service << 'EOF'
[Unit]
Description=Gäld scheduler run
After=network.target redis.service postgresql.service

[Service]
Type=oneshot
User=www
Group=www
WorkingDirectory=/srv/www/gaeld
ExecStart=/usr/bin/php artisan schedule:run
EOF

cat > %{buildroot}%{_unitdir}/gaeld-scheduler.timer << 'EOF'
[Unit]
Description=Run the Gäld scheduler every minute

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
AccuracySec=15s
Unit=gaeld-scheduler.service

[Install]
WantedBy=timers.target
EOF

install -d %{buildroot}%{_tmpfilesdir}
cat > %{buildroot}%{_tmpfilesdir}/gaeld.conf << 'EOF'
d /run/php-fpm 0755 www www -
d /var/lib/gaeld/backups 0750 www www -
EOF

# Drop development-only trees that are not part of the runtime app.
rm -rf %{buildroot}/srv/www/%{name}/.github \
	%{buildroot}/srv/www/%{name}/storage/framework/testing

%post
chown -R www:www /srv/www/gaeld/storage /srv/www/gaeld/bootstrap/cache /var/lib/gaeld
chmod -R u+rwX,g+rwX /srv/www/gaeld/storage /srv/www/gaeld/bootstrap/cache
if [ "$1" -ge 2 ] && grep -q '^APP_KEY=base64:' /etc/gaeld/gaeld.env 2>/dev/null; then
	runuser -u www -- /usr/bin/php /srv/www/gaeld/artisan gaeld:update --no-interaction || :
fi

%preun
if [ "$1" = 0 ]; then
	systemctl disable --now gaeld-horizon.service gaeld-scheduler.timer php-fpm@gaeld >/dev/null 2>&1 || :
fi

%files
%doc README.install.omv LICENSE README.md
%{_bindir}/gaeld
%{_unitdir}/gaeld-horizon.service
%{_unitdir}/gaeld-scheduler.service
%{_unitdir}/gaeld-scheduler.timer
%dir %attr(0750,root,www) %{_sysconfdir}/%{name}
%attr(0640,root,www) %config(noreplace) %{_sysconfdir}/%{name}/gaeld.env
%dir %attr(0750,www,www) /var/lib/%{name}
%dir %attr(0750,www,www) /var/lib/%{name}/backups
%config(noreplace) %{_sysconfdir}/php-fpm-instances.d/gaeld.conf
%{_tmpfilesdir}/gaeld.conf
/srv/www/%{name}

%files nginx
%config(noreplace) %{_sysconfdir}/nginx/sites-available/gaeld.conf

%files apache
%config(noreplace) %{_sysconfdir}/httpd/conf/webapps.d/gaeld.conf
