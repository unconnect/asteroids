# The pygbag bundle is built before this image (scripts/build_web.sh), so
# this is a pure static-file copy. Building pygbag inside the image would run
# the whole Python toolchain (and, on arm64 hosts, under QEMU emulation) and
# take many minutes for no benefit -- the payload is a handful of static
# files plus a game archive whose name varies with the checkout directory
# (see docker/nginx.conf and the build verification in build_web.sh; nothing
# here hardcodes it).
FROM nginx:alpine

COPY build/web /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# proxy_cache_path (docker/nginx.conf) requires this directory to already
# exist and be writable by the user nginx's worker processes run as; nginx
# does not create cache directories itself.
RUN mkdir -p /var/cache/nginx/cdn && chown -R nginx:nginx /var/cache/nginx/cdn

EXPOSE 80
