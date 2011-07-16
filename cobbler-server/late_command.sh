#!/bin/bash

{
fb_d="/root/first-boot.d"
mkdir -p "$fb_d"
sed -i '/^exit 0/d' /etc/rc.local
cat >> /etc/rc.local <<EOF
## first boot finish stuff
if [ ! -f "$fb_d.done" ]; then
   run-parts "$fb_d" 2>&1 | tee "${fb_d}.log"
   touch "$fb_d.done"
fi
EOF

cat >"$fb_d/10-addl-pkgs" <<"EOF"
#!/bin/sh
pkgs="ubuntu-orchestra-provisioning-server cman"
[ -t 1 ] || {
   unset DEBIAN_HAS_FRONTEND DEBIAN_FRONTEND DEBCONF_REDIR DEBCONF_OLD_FD_BASE;
   export DEBIAN_FRONTEND=noninteractive;
}
if [ "$(lsb_release --codename --short)" = "natty" ]; then
   for p in ppa:orchestra/ppa ppa:dotdee/ppa; do apt-add-repository $p; done
fi
apt-get update
apt-get install --assume-yes ${pkgs}
EOF

cat > "$fb_d/99-halt" <<EOF
#!/bin/sh
touch "$fb_d.done"
/sbin/poweroff
EOF

cat >"$fb_d/50-setup-cobbler" <<"EOF"
#!/bin/sh

cp -a /etc/cobbler/settings /etc/cobbler/settings.dist
sed -i 's,^next_server: .*,next_server: cobbler,' /etc/cobbler/settings
sed -i 's,^server: .*,server: cobbler,' /etc/cobbler/settings

# https://fedorahosted.org/cobbler/wiki/CobblerWebInterface
# htdigest /etc/cobbler/users.digest "Cobbler" cobbler
cat > /etc/cobbler/users.digest <<ENDUSERDIGEST
cobbler:Cobbler:a2d6bae81669d707b72c0bd9806e01f3
ENDUSERDIGEST

seed="/var/lib/cobbler/kickstarts/ensemble.preseed"
cat > "$seed" <<"ENDPRESEED"
# Ubuntu Server Quick Install for Orchestra deployed systems
# by Dustin Kirkland <kirkland@ubuntu.com>
#  * Documentation: http://bit.ly/uquick-doc

d-i     debian-installer/locale string en_US.UTF-8
d-i     debian-installer/splash boolean false
d-i     console-setup/ask_detect        boolean false
d-i     console-setup/layoutcode        string us
d-i     console-setup/variantcode       string 
d-i     netcfg/get_nameservers  string 
d-i     netcfg/get_ipaddress    string 
d-i     netcfg/get_netmask      string 255.255.255.0
d-i     netcfg/get_gateway      string 
d-i     netcfg/confirm_static   boolean true
d-i     clock-setup/utc boolean true
d-i     partman-auto/method string regular
d-i     partman-lvm/device_remove_lvm boolean true
d-i     partman-lvm/confirm boolean true
d-i     partman/confirm_write_new_label boolean true
d-i     partman/choose_partition        select Finish partitioning and write changes to disk
d-i     partman/confirm boolean true
d-i     partman/confirm_nooverwrite boolean true
d-i     partman/default_filesystem string ext4
d-i     clock-setup/utc boolean true
d-i     clock-setup/ntp boolean true
d-i     clock-setup/ntp-server  string ntp.ubuntu.com
d-i     base-installer/kernel/image     string linux-server
d-i     passwd/root-login       boolean false
d-i     passwd/make-user        boolean true
d-i     passwd/user-fullname    string ubuntu
d-i     passwd/username string ubuntu
d-i     passwd/user-password-crypted    password $6$.1eHH0iY$ArGzKX2YeQ3G6U.mlOO3A.NaL22Ewgz8Fi4qqz.Ns7EMKjEJRIW2Pm/TikDptZpuu7I92frytmk5YeL.9fRY4.
d-i     passwd/user-uid string 
d-i     user-setup/allow-password-weak  boolean false
d-i     user-setup/encrypt-home boolean false
d-i     passwd/user-default-groups      string adm cdrom dialout lpadmin plugdev sambashare
d-i     apt-setup/services-select       multiselect security
d-i     apt-setup/security_host string security.ubuntu.com
d-i     apt-setup/security_path string /ubuntu
d-i     debian-installer/allow_unauthenticated  string false
d-i     pkgsel/upgrade  select safe-upgrade
d-i     pkgsel/language-packs   multiselect 
d-i     pkgsel/update-policy    select none
d-i     pkgsel/updatedb boolean true
d-i     grub-installer/skip     boolean false
d-i     lilo-installer/skip     boolean false
d-i     grub-installer/only_debian      boolean true
d-i     grub-installer/with_other_os    boolean true
d-i     finish-install/keep-consoles    boolean false
d-i     finish-install/reboot_in_progress       note 
d-i     cdrom-detect/eject      boolean true
d-i     debian-installer/exit/halt      boolean false
d-i     debian-installer/exit/poweroff  boolean false
d-i     pkgsel/include string ubuntu-orchestra-client $getVar('EXTRA_PACKAGES','')
byobu   byobu/launch-by-default boolean true
d-i   preseed/late_command string true && \
   $getVar('ENSEMBLE_LATE_COMMAND', 'true') && \
   wget "http://$http_server:$http_port/cblr/svc/op/nopxe/system/$system_name" -O /dev/null && \
   true
ENDPRESEED


mkdir -p /var/lib/cobbler/isos
cd /var/lib/cobbler/isos
set -- ${DISTS:-natty:i386 natty:amd64 oneiric:i386 oneiric:amd64}
mirror="${MIRROR:-http://archive.ubuntu.com/ubuntu}"
for t in "$@"; do
   rel=${t%:*}; arch=${t#*:}
   iso=$rel-$arch-mini.iso
   [ -f "$iso" ] && continue
   u=$mirror/dists/$rel/main/installer-$arch/current/images/netboot/mini.iso
   wget -O "$iso" "$u"
done

for t in "$@"; do
   rel=${t%:*}; arch=${t#*:}
   xa=$arch; [ "$arch" = "amd64" ] && xa=x86_64
   mount -o loop $rel-$arch-mini.iso /mnt 
   cobbler import --name=$rel-$arch --path=/mnt --breed=ubuntu --os-version=$rel --arch=$xa
   umount /mnt
   name=$rel-$xa
   ## cobbler wants to name distro and the default profile as <version>-<xa> (x86_64, not amd64)
   ## so, we just let it be.  if we renamed, we'd have to do both profile and distribution
   ## [ "$xa" != "$arch" ] &&
   ##    cobbler profile rename --name $name --newname $rel-$arch &&
   ##    cobbler distro rename --name $name --newname $rel-$arch &&
   ##    name=$rel-$arch &&
   ##    cobbler profile edit --name $name --distro $name
   #fi
   cobbler profile edit --name $name --kopts="priority=critical locale=en_US"
   cobbler profile add --parent $name --name $name-ensemble --kickstart=$seed 
done

# set up the webdav host
a2enmod dav
a2enmod dav_fs
service apache2 restart
cat > /etc/apache2/conf.d/dav.conf <<ENDWEBDAV
Alias /webdav /var/lib/webdav
 
<Directory /var/lib/webdav>
Order allow,deny
allow from all
Dav On
</Directory>
ENDWEBDAV
#EOF

EOF

chmod u+x "$fb_d"/*
} 2>&1 | tee /root/late.log
