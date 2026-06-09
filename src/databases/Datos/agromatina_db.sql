-- ============================================================ 
-- Base de datos WEB: agromatina_web 
-- Motor: MySQL 8 / InnoDB / utf8mb4 
-- Proyecto: Sistema web de ventas en linea Agromatina (IF7100) 
-- 
-- Esta BD es SEPARADA de violette_db (escritorio de Jakob). 
--   - violette_db    = fuente de verdad (catalogo real, ventas fiscales, facturacion Hacienda) 
--   - agromatina_web = catalogo replicado (solo lectura) + cuentas web + pedidos + cotizaciones 
-- 
-- El catalogo llega por SINCRONIZACION via API (proceso P4, push desde el escritorio): 
-- el escritorio sube la imagen a Cloudinary, obtiene el link y le hace POST a la API 
-- de FastAPI, que hace upsert por 'codigo' en las tablas del catalogo. 
-- 
-- NOTA: El Administrador (Jakob) NO entra a la web (RN-02). Su usuario vive en 
-- violette_db.users (escritorio). Por eso aqui NO hay tabla de administradores. 

-- ============================================================ 
CREATE DATABASE IF NOT EXISTS agromatina_web 
DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; 
USE agromatina_web;

CREATE TABLE categorias (
    id INT PRIMARY KEY AUTO_INCREMENT,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL,
    activa TINYINT(1) NOT NULL DEFAULT 1,
    posicion INT NOT NULL DEFAULT 0,
    last_synced_at DATETIME DEFAULT NULL
)  ENGINE=INNODB;

CREATE TABLE productos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(150) NOT NULL,
    descripcion VARCHAR(500) DEFAULT NULL,
    precio DECIMAL(12 , 2 ) NOT NULL,
    precio_oferta DECIMAL(12 , 2 ) DEFAULT NULL,
    en_oferta TINYINT(1) NOT NULL DEFAULT 0,
    mas_vendido TINYINT(1) NOT NULL DEFAULT 0,
    stock DECIMAL(12 , 3 ) NOT NULL DEFAULT 0,
    categoria_id INT DEFAULT NULL,
    image_url VARCHAR(500) DEFAULT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    last_synced_at DATETIME DEFAULT NULL,
    KEY ix_productos_categoria (categoria_id),
    CONSTRAINT fk_productos_categoria FOREIGN KEY (categoria_id)
	REFERENCES categorias (id)
)  ENGINE=INNODB;

-- ============================================================ 
CREATE TABLE clientes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(50) NOT NULL,
    primer_apellido VARCHAR(50) NOT NULL,
    segundo_apellido VARCHAR(50) DEFAULT NULL,
    tipo_identificacion ENUM('cedula', 'dimex', 'pasaporte') NOT NULL,
    numero_identificacion VARCHAR(50) NOT NULL,
    telefono VARCHAR(15) NOT NULL,
    UNIQUE KEY uq_clientes_identificacion (tipo_identificacion , numero_identificacion)
)  ENGINE=INNODB; 

CREATE TABLE direccion (
	id INT PRIMARY KEY AUTO_INCREMENT,
    id_cliente INT,
    provincia VARCHAR(50) DEFAULT NULL,  
	canton VARCHAR(80) DEFAULT NULL,  
	direccion VARCHAR(255) NOT NULL, 
	created_at DATETIME DEFAULT (NOW()), 
	updated_at DATETIME DEFAULT (NOW()), 
    CONSTRAINT fk_id_cliente FOREIGN KEY (id_cliente) REFERENCES clientes (id) ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE usuarios ( 
	id INT PRIMARY KEY AUTO_INCREMENT, 
	cliente_id INT NOT NULL UNIQUE,       -- 1 usuario = 1 cliente (FK real, no polimorfica) 
	rol VARCHAR(20)  NOT NULL DEFAULT 'cliente', 
	correo VARCHAR(255) NOT NULL UNIQUE, 
	clave VARCHAR(255) NOT NULL,              -- HASH (bcrypt/argon2), NUNCA texto plano 
	estado ENUM('no_verificada','verificada') NOT NULL DEFAULT 'no_verificada', -- CU-06/CU-07 
	ultimo_acceso DATETIME DEFAULT NULL,          -- para refresco de pagina 
	tk_refresh VARCHAR(255) DEFAULT NULL,          -- token de sesion / refresh (si no usas JWT puro) 
	created_at DATETIME DEFAULT (NOW()), 
	CONSTRAINT fk_usuarios_cliente 
	FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE 
) ENGINE=InnoDB; 

-- Tokens transitorios: verificacion de correo (24h, CU-07) y recuperacion (30min, CU-10). 
-- Separados porque tienen vencimiento distinto, pueden coexistir y se marcan como usados. 
CREATE TABLE tokens_verificacion ( 
	id INT PRIMARY KEY AUTO_INCREMENT, 
	usuario_id  INT NOT NULL, 
	tipo ENUM('verificacion','recuperacion') NOT NULL, 
	token VARCHAR(255) NOT NULL, 
	expira_en DATETIME NOT NULL, 
	usado TINYINT(1) NOT NULL DEFAULT 0, 
	created_at  DATETIME DEFAULT (NOW()), 
	KEY ix_tokens_usuario (usuario_id), 
	KEY ix_tokens_token (token), 
	CONSTRAINT fk_tokens_usuario 
	FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE 
) ENGINE=InnoDB; 

-- ============================================================ 
-- 3) PEDIDOS WEB (la "orden" del cliente en la tienda) 
--    NO es la venta fiscal. La venta fiscal + factura viven en 
--    violette_db (escritorio). El pedido guarda solo una referencia. 
--    El carrito NO se modela aqui: vive en sessionStorage (CU-05). 
-- ============================================================ 
CREATE TABLE pedidos ( 
	id INT PRIMARY KEY AUTO_INCREMENT, 
	numero_orden VARCHAR(20)  NOT NULL UNIQUE,   -- numero visible (CU-13/14/15) 
	cliente_id INT NOT NULL, 
	metodo_pago ENUM('sinpe','paypal') NOT NULL, 
	estado ENUM('pendiente_validacion','confirmado','cancelada') NOT NULL DEFAULT 'pendiente_validacion', 
	total DECIMAL(12,2) NOT NULL, 
	-- Direccion de entrega CONGELADA al momento del pedido (no FK al perfil, 
	-- porque el cliente puede cambiar su direccion despues) 
	-- Comprobante: para PayPal lo genera la web (link Cloudinary o endpoint propio); 
	-- para SINPE queda NULL hasta que Jakob emita la factura desde el escritorio. 
	comprobante_pdf_url VARCHAR(500) DEFAULT NULL, 

	-- Trazabilidad hacia la venta fiscal del escritorio (consecutivo/clave de factura) 
	referencia_factura_escritorio VARCHAR(50)  DEFAULT NULL, 
	created_at DATETIME DEFAULT (NOW()), 
	updated_at DATETIME DEFAULT (NOW()), 
	KEY ix_pedidos_cliente (cliente_id), 
	KEY ix_pedidos_estado (estado), 
	CONSTRAINT fk_pedidos_cliente FOREIGN KEY (cliente_id) REFERENCES clientes (id) 
) ENGINE=InnoDB;

-- Lineas del pedido con SNAPSHOT del producto (precio/nombre congelados). 
-- OJO: a proposito NO hay FK a 'productos', para que el catalogo replicado 
-- se pueda reconstruir sin romper pedidos historicos. 
CREATE TABLE pedido_detalles (
	id INT PRIMARY KEY AUTO_INCREMENT,
    pedido_id INT NOT NULL,
    producto_codigo VARCHAR(50) NOT NULL,
    producto_nombre VARCHAR(150) NOT NULL,
    precio_unitario DECIMAL(12 , 2 ) NOT NULL,
    cantidad DECIMAL(12 , 3 ) NOT NULL,
    subtotal DECIMAL(12 , 2 ) NOT NULL,
    KEY ix_detalles_pedido (pedido_id),
    CONSTRAINT fk_detalles_pedido FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE
)  ENGINE=INNODB; 

-- Resultado de la pasarela PayPal (solo aplica a pagos PayPal, CU-14). 
CREATE TABLE transacciones_pago ( 
	id INT PRIMARY KEY AUTO_INCREMENT, 
	pedido_id INT NOT NULL, 
	proveedor VARCHAR(20)  NOT NULL DEFAULT 'paypal', 
	transaccion_externa VARCHAR(100) DEFAULT NULL,    -- id que devuelve PayPal 
	estado ENUM('iniciada','completada','fallida','cancelada') NOT NULL DEFAULT 'iniciada', 
	monto DECIMAL(12,2) NOT NULL, 
	respuesta_raw TEXT DEFAULT NULL,     -- JSON crudo del webhook/respuesta 
	created_at DATETIME DEFAULT (NOW()), 
	KEY ix_transacciones_pedido (pedido_id), 
	CONSTRAINT fk_transacciones_pedido 
	FOREIGN KEY (pedido_id) REFERENCES pedidos (id) 
) ENGINE=InnoDB; 

-- ============================================================ 
-- 4) COTIZACIONES (CU-16) 
--    Liviana y SUELTA: no genera pedido ni venta. Solo se notifica 
--    a Jakob por WhatsApp. Aqui guardamos el registro y los links. 
-- ============================================================ 
CREATE TABLE solicitudes_cotizacion ( 
	id INT PRIMARY KEY AUTO_INCREMENT, 
	cliente_id INT DEFAULT NULL,            -- nulo si el solicitante es anonimo 
	nombre VARCHAR(150) NOT NULL, 
	correo VARCHAR(255) NOT NULL, 
	telefono VARCHAR(15)  NOT NULL, 
	asunto VARCHAR(150) NOT NULL DEFAULT 'Cotizacion', 
	mensaje TEXT NOT NULL, 
	estado ENUM('enviada','atendida') NOT NULL DEFAULT 'enviada', 
	created_at DATETIME DEFAULT (NOW()), 
	KEY ix_cotizacion_cliente (cliente_id), 
	CONSTRAINT fk_cotizacion_cliente 
	FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE SET NULL 
) ENGINE=InnoDB;

-- Adjuntos de la cotizacion (max 5 segun CU-16): PDF/PNG/JPEG subidos a Cloudinary. 
CREATE TABLE cotizacion_archivos (
	id INT PRIMARY KEY AUTO_INCREMENT,
    cotizacion_id INT NOT NULL,
    archivo_url VARCHAR(500) NOT NULL,
    tipo VARCHAR(10) DEFAULT NULL,
    KEY ix_archivos_cotizacion (cotizacion_id),
    CONSTRAINT fk_archivos_cotizacion FOREIGN KEY (cotizacion_id) REFERENCES solicitudes_cotizacion (id) ON DELETE CASCADE
)  ENGINE=INNODB; 