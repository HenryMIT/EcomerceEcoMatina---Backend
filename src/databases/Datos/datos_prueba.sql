-- ============================================================
  -- Datos de prueba — agromatina_web
  -- Solo sentencias INSERT. IDs explicitos para coherencia de FKs.
  -- Asume tablas recien creadas (sin registros previos).
  -- ============================================================
  USE agromatina_web;
  
  -- ------------------------------------------------------------
  -- 1) categorias (padre de productos)
  -- ------------------------------------------------------------
  INSERT INTO categorias (id, codigo, nombre, activa, posicion, last_synced_at) VALUES
  (1, 'CAT-HER', 'Herramientas',        1, 1, '2026-05-20 08:00:00'),
  (2, 'CAT-PIN', 'Pinturas',            1, 2, '2026-05-20 08:00:00'),
  (3, 'CAT-FON', 'Fontaneria',          1, 3, '2026-05-20 08:00:00'),
  (4, 'CAT-ELE', 'Electricidad',        1, 4, '2026-05-20 08:00:00'),
  (5, 'CAT-CON', 'Construccion',        1, 5, '2026-05-20 08:00:00'),
  (6, 'CAT-JAR', 'Jardineria',          1, 6, '2026-05-20 08:00:00'),
  (7, 'CAT-FER', 'Ferreteria General',  1, 7, '2026-05-20 08:00:00'),
  (8, 'CAT-SEG', 'Seguridad',           1, 8, '2026-05-20 08:00:00');

  -- ------------------------------------------------------------
  -- 2) productos (categoria_id -> categorias.id)
  --    PROD-010 esta en_oferta pero activo=0 (debe filtrarse en RF-01).
  --    PROD-003, 005, 008 no estan en oferta.
  -- ------------------------------------------------------------
  INSERT INTO productos
  (id, codigo, nombre, descripcion, precio, precio_oferta, en_oferta, mas_vendido, stock, categoria_id, activo, last_synced_at) VALUES
  (1,  'PROD-001', 'Taladro percutor 1/2" 650W',        'Taladro percutor electrico de 650W con mandril de media pulgada, ideal para concreto y madera.', 45000.00, 38250.00, 1, 1,
  25.000,  1, 1, '2026-05-21 09:15:00'),
  (2,  'PROD-002', 'Juego de destornilladores 6 piezas','Set de 6 destornilladores planos y de cruz con mango ergonomico antideslizante.',                  8500.00,  6800.00,  1, 0,
  120.000, 1, 1, '2026-05-21 09:15:00'),
  (3,  'PROD-003', 'Pintura latex blanco 1 galon',      'Pintura latex lavable color blanco, acabado mate, rendimiento de 40 metros cuadrados por galon.', 12500.00, NULL,     0, 1,
  80.000,  2, 1, '2026-05-21 09:15:00'),
  (4,  'PROD-004', 'Brocha 3 pulgadas cerda natural',   'Brocha profesional de 3 pulgadas con cerda natural para pinturas y barnices.',                    2300.00,  1840.00,  1, 0,
  200.000, 2, 1, '2026-05-21 09:15:00'),
  (5,  'PROD-005', 'Tubo PVC 1/2" x 6m',                'Tuberia PVC de media pulgada por 6 metros para conduccion de agua potable.',                      3200.00,  NULL,     0, 1,
  300.000, 3, 1, '2026-05-21 09:15:00'),
  (6,  'PROD-006', 'Llave de paso bronce 1/2"',         'Llave de paso de bronce de media pulgada, rosca estandar, alta durabilidad.',                     4800.00,  3600.00,  1, 0,
  60.000,  3, 1, '2026-05-21 09:15:00'),
  (7,  'PROD-007', 'Cable THHN #12 (metro)',            'Cable electrico THHN calibre 12, venta por metro, aislamiento termoplastico.',                    850.00,   720.00,   1, 1,
  1000.000,4, 1, '2026-05-21 09:15:00'),
  (8,  'PROD-008', 'Saco de cemento 50kg',              'Cemento gris de uso general en saco de 50 kilogramos para obra civil.',                           7200.00,  NULL,     0, 1,
  150.000, 5, 1, '2026-05-21 09:15:00'),
  (9,  'PROD-009', 'Pala cuadrada mango madera',        'Pala cuadrada de acero con mango de madera reforzado para jardineria y construccion.',            6500.00,  5200.00,  1, 0,
  40.000,  6, 1, '2026-05-21 09:15:00'),
  (10, 'PROD-010', 'Candado de seguridad 50mm',         'Candado de laton de 50mm con dos llaves, resistente a la corrosion. Producto descontinuado.',     5500.00,  4400.00,  1, 0,
  0.000,   8, 0, '2026-05-21 09:15:00');

  -- ------------------------------------------------------------
  -- 3) producto_imagenes (producto_id -> productos.id)
  --    PROD-002 sin imagen principal (es_principal=0): prueba el fallback por posicion.
  -- ------------------------------------------------------------
  INSERT INTO producto_imagenes (id, producto_id, url, es_principal, posicion) VALUES
  (1,  1,  'https://res.cloudinary.com/agromatina/image/upload/v1/productos/prod-001-1.jpg', 1, 1),
  (2,  1,  'https://res.cloudinary.com/agromatina/image/upload/v1/productos/prod-001-2.jpg', 0, 2),
  (3,  2,  'https://res.cloudinary.com/agromatina/image/upload/v1/productos/prod-002-1.jpg', 0, 1),
  (4,  3,  'https://res.cloudinary.com/agromatina/image/upload/v1/productos/prod-003-1.jpg', 1, 1),
  (5,  4,  'https://res.cloudinary.com/agromatina/image/upload/v1/productos/prod-004-1.jpg', 1, 1),
  (6,  5,  'https://res.cloudinary.com/agromatina/image/upload/v1/productos/prod-005-1.jpg', 1, 1),
  (7,  6,  'https://res.cloudinary.com/agromatina/image/upload/v1/productos/prod-006-1.jpg', 1, 1),
  (8,  6,  'https://res.cloudinary.com/agromatina/image/upload/v1/productos/prod-006-2.jpg', 0, 2),
  (9,  7,  'https://res.cloudinary.com/agromatina/image/upload/v1/productos/prod-007-1.jpg', 1, 1),
  (10, 8,  'https://res.cloudinary.com/agromatina/image/upload/v1/productos/prod-008-1.jpg', 1, 1),
  (11, 9,  'https://res.cloudinary.com/agromatina/image/upload/v1/productos/prod-009-1.jpg', 1, 1),
  (12, 10, 'https://res.cloudinary.com/agromatina/image/upload/v1/productos/prod-010-1.jpg', 1, 1);

  -- ------------------------------------------------------------
  -- 4) clientes (padre de direccion, usuarios, pedidos, cotizaciones)
  -- ------------------------------------------------------------
  INSERT INTO clientes
  (id, nombre, primer_apellido, segundo_apellido, tipo_identificacion, numero_identificacion, telefono) VALUES
  (1, 'Ana',    'Rojas',     'Mora',    'cedula',    '110450789',    '88012345'),
  (2, 'Carlos', 'Jimenez',   'Vargas',  'cedula',    '207890456',    '87023456'),
  (3, 'Maria',  'Solano',    NULL,      'dimex',     '155812340021', '86034567'),
  (4, 'Jose',   'Hernandez', 'Castro',  'cedula',    '304560123',    '85045678'),
  (5, 'Luis',   'Mendez',    'Aguilar', 'pasaporte', 'A0123456',     '84056789'),
  (6, 'Sofia',  'Quiros',    'Leon',    'cedula',    '113450987',    '83067890');

  -- ------------------------------------------------------------
  -- 5) direccion (id_cliente -> clientes.id)
  -- ------------------------------------------------------------
  INSERT INTO direccion (id, id_cliente, provincia, canton, direccion, created_at, updated_at) VALUES
  (1, 1, 'Limon',     'Matina',    '200m este de la escuela de Matina, casa verde', '2026-05-22 10:00:00', '2026-05-22 10:00:00'),
  (2, 2, 'Limon',     'Siquirres', 'Barrio El Carmen, casa numero 45',              '2026-05-22 10:05:00', '2026-05-22 10:05:00'),
  (3, 3, 'Limon',     'Matina',    'Frente al parque central, segundo piso',        '2026-05-22 10:10:00', '2026-05-22 10:10:00'),
  (4, 4, 'Cartago',   'Turrialba', 'Avenida 3, calle 5, porton negro',              '2026-05-22 10:15:00', '2026-05-22 10:15:00'),
  (5, 5, 'San Jose',  'Central',   'Edificio Torres del Este, apartamento 12',      '2026-05-22 10:20:00', '2026-05-22 10:20:00'),
  (6, 6, 'Limon',     'Matina',    'Calle ancha, 100m norte del EBAIS',             '2026-05-22 10:25:00', '2026-05-22 10:25:00'),
  (7, 1, 'Limon',     'Batan',     'Plaza Batan, 50m sur del super',                '2026-05-23 11:00:00', '2026-05-23 11:00:00');

  -- ------------------------------------------------------------
  -- 6) usuarios (cliente_id -> clientes.id, UNIQUE)
  --    clave = hash bcrypt de ejemplo (formato realista, no texto plano).
  -- ------------------------------------------------------------
  INSERT INTO usuarios
  (id, cliente_id, rol, correo, clave, estado, ultimo_acceso, tk_refresh, created_at) VALUES
  (1, 1, 'cliente', 'ana.rojas@example.com',      '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyOpqQ2mF1tG2e', 'verificada',    '2026-06-08 18:30:00', 'rt_ana_9f2a4c7b1e',
  '2026-05-22 10:00:00'),
  (2, 2, 'cliente', 'carlos.jimenez@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyOpqQ2mF1tG2e', 'verificada',    '2026-06-07 09:12:00', 'rt_carlos_3b8d1a',
  '2026-05-22 10:05:00'),
  (3, 3, 'cliente', 'maria.solano@example.com',   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyOpqQ2mF1tG2e', 'no_verificada', NULL,                  NULL,
  '2026-05-22 10:10:00'),
  (4, 4, 'cliente', 'jose.hernandez@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyOpqQ2mF1tG2e', 'verificada',    '2026-06-06 14:45:00', 'rt_jose_7c2e9f',
  '2026-05-22 10:15:00'),
  (5, 5, 'cliente', 'luis.mendez@example.com',    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyOpqQ2mF1tG2e', 'no_verificada', NULL,                  NULL,
  '2026-05-22 10:20:00'),
  (6, 6, 'cliente', 'sofia.quiros@example.com',   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyOpqQ2mF1tG2e', 'verificada',    '2026-06-09 07:50:00', 'rt_sofia_1d6b8a',
  '2026-05-22 10:25:00');

  -- ------------------------------------------------------------
  -- 7) tokens_verificacion (usuario_id -> usuarios.id)
  -- ------------------------------------------------------------
  INSERT INTO tokens_verificacion (id, usuario_id, tipo, token, expira_en, usado, created_at) VALUES
  (1, 3, 'verificacion', 'tok_verif_maria_4a7b9c2d1e', '2026-06-10 10:10:00', 0, '2026-06-09 10:10:00'),
  (2, 5, 'verificacion', 'tok_verif_luis_8f3c1a6b9d',  '2026-06-10 10:20:00', 0, '2026-06-09 10:20:00'),
  (3, 1, 'recuperacion', 'tok_recup_ana_2e9d4c7a1b',   '2026-06-09 20:30:00', 0, '2026-06-09 20:00:00'),
  (4, 2, 'verificacion', 'tok_verif_carlos_1a2b3c4d5e','2026-05-23 10:05:00', 1, '2026-05-22 10:05:00');

  -- ------------------------------------------------------------
  -- 8) pedidos (cliente_id -> clientes.id)
  --    total coincide con la suma de subtotales en pedido_detalles.
  -- ------------------------------------------------------------
  INSERT INTO pedidos
  (id, numero_orden, cliente_id, metodo_pago, estado, total, comprobante_pdf_url, referencia_factura_escritorio, created_at, updated_at) VALUES
  (1, 'ORD-2026-0001', 1, 'paypal', 'confirmado',             45050.00, 'https://res.cloudinary.com/agromatina/raw/upload/v1/comprobantes/ORD-2026-0001.pdf', NULL,       '2026-06-01
  12:00:00', '2026-06-01 12:05:00'),
  (2, 'ORD-2026-0002', 2, 'sinpe',  'pendiente_validacion',   6800.00,  NULL,                                                                                NULL,       '2026-06-03
  15:30:00', '2026-06-03 15:30:00'),
  (3, 'ORD-2026-0003', 1, 'sinpe',  'confirmado',             5440.00,  NULL,                                                                                'FE-00123', '2026-06-04
  09:20:00', '2026-06-05 10:00:00'),
  (4, 'ORD-2026-0004', 4, 'paypal', 'confirmado',             720.00,   'https://res.cloudinary.com/agromatina/raw/upload/v1/comprobantes/ORD-2026-0004.pdf', NULL,       '2026-06-05
  16:40:00', '2026-06-05 16:42:00'),
  (5, 'ORD-2026-0005', 6, 'sinpe',  'cancelada',              5200.00,  NULL,                                                                                NULL,       '2026-06-06
  11:10:00', '2026-06-06 18:00:00'),
  (6, 'ORD-2026-0006', 2, 'paypal', 'confirmado',             12000.00, 'https://res.cloudinary.com/agromatina/raw/upload/v1/comprobantes/ORD-2026-0006.pdf', NULL,       '2026-06-08
  13:25:00', '2026-06-08 13:28:00');

  -- ------------------------------------------------------------
  -- 9) pedido_detalles (pedido_id -> pedidos.id) — snapshot del producto
  -- ------------------------------------------------------------
  INSERT INTO pedido_detalles
  (id, pedido_id, producto_codigo, producto_nombre, precio_unitario, cantidad, subtotal) VALUES
  (1,  1, 'PROD-001', 'Taladro percutor 1/2" 650W',         38250.00, 1.000, 38250.00),
  (2,  1, 'PROD-002', 'Juego de destornilladores 6 piezas', 6800.00,  1.000, 6800.00),
  (3,  2, 'PROD-002', 'Juego de destornilladores 6 piezas', 6800.00,  1.000, 6800.00),
  (4,  3, 'PROD-006', 'Llave de paso bronce 1/2"',          3600.00,  1.000, 3600.00),
  (5,  3, 'PROD-004', 'Brocha 3 pulgadas cerda natural',    1840.00,  1.000, 1840.00),
  (6,  4, 'PROD-007', 'Cable THHN #12 (metro)',             720.00,   1.000, 720.00),
  (7,  5, 'PROD-009', 'Pala cuadrada mango madera',         5200.00,  1.000, 5200.00),
  (8,  6, 'PROD-002', 'Juego de destornilladores 6 piezas', 6800.00,  1.000, 6800.00),
  (9,  6, 'PROD-009', 'Pala cuadrada mango madera',         5200.00,  1.000, 5200.00);

  -- ------------------------------------------------------------
  -- 10) transacciones_pago (pedido_id -> pedidos.id) — solo PayPal
  -- ------------------------------------------------------------
  INSERT INTO transacciones_pago
  (id, pedido_id, proveedor, transaccion_externa, estado, monto, respuesta_raw, created_at) VALUES
  (1, 1, 'paypal', 'PAYID-ABC123XYZ', 'completada', 45050.00, '{"status":"COMPLETED","payer":"ana.rojas@example.com"}',     '2026-06-01 12:04:00'),
  (2, 4, 'paypal', 'PAYID-DEF456UVW', 'completada', 720.00,   '{"status":"COMPLETED","payer":"jose.hernandez@example.com"}','2026-06-05 16:41:00'),
  (3, 6, 'paypal', 'PAYID-GHI789RST', 'fallida',    12000.00, '{"status":"DENIED","reason":"INSTRUMENT_DECLINED"}',         '2026-06-08 13:26:00'),
  (4, 6, 'paypal', 'PAYID-GHI790RSU', 'completada', 12000.00, '{"status":"COMPLETED","payer":"carlos.jimenez@example.com"}','2026-06-08 13:27:30');

  -- ------------------------------------------------------------
  -- 11) solicitudes_cotizacion (cliente_id -> clientes.id, NULL = anonimo)
  -- ------------------------------------------------------------
  INSERT INTO solicitudes_cotizacion
  (id, cliente_id, nombre, correo, telefono, asunto, mensaje, estado, created_at) VALUES
  (1, 1,    'Ana Rojas Mora',        'ana.rojas@example.com',      '88012345', 'Cotizacion',                 'Necesito cotizar 50 sacos de cemento y 20 tubos PVC para una construccion
  en Matina.', 'enviada',  '2026-06-02 09:00:00'),
  (2, 4,    'Jose Hernandez Castro', 'jose.hernandez@example.com', '85045678', 'Cotizacion materiales',      'Solicito precio por mayoreo de cable THHN y tubería electrica.',
              'atendida', '2026-06-03 14:30:00'),
  (3, NULL, 'Pedro Campos Ureña',    'pedro.campos@example.com',   '70123456', 'Cotizacion',                 'Quisiera saber el precio de herramientas electricas para un taller
  pequeño.',          'enviada',  '2026-06-04 17:45:00'),
  (4, 2,    'Carlos Jimenez Vargas', 'carlos.jimenez@example.com', '87023456', 'Cotizacion pintura',         'Cotizar 30 galones de pintura latex blanca y brochas asociadas.',
              'enviada',  '2026-06-06 08:15:00'),
  (5, NULL, 'Laura Mata Solis',      'laura.mata@example.com',     '60987654', 'Cotizacion',                 'Necesito candados y elementos de seguridad para bodega.',
              'atendida', '2026-06-07 19:20:00'),
  (6, 6,    'Sofia Quiros Leon',     'sofia.quiros@example.com',   '83067890', 'Cotizacion jardineria',      'Cotizar palas, rastrillos y mangueras para proyecto de jardineria
  municipal.',        'enviada',  '2026-06-08 10:05:00');

  -- ------------------------------------------------------------
  -- 12) cotizacion_archivos (cotizacion_id -> solicitudes_cotizacion.id)
  -- ------------------------------------------------------------
  INSERT INTO cotizacion_archivos (id, cotizacion_id, archivo_url, tipo) VALUES
  (1, 1, 'https://res.cloudinary.com/agromatina/raw/upload/v1/cotizaciones/cot-001-plano.pdf',     'pdf'),
  (2, 1, 'https://res.cloudinary.com/agromatina/image/upload/v1/cotizaciones/cot-001-foto.jpeg',   'jpeg'),
  (3, 3, 'https://res.cloudinary.com/agromatina/image/upload/v1/cotizaciones/cot-003-lista.png',   'png'),
  (4, 4, 'https://res.cloudinary.com/agromatina/raw/upload/v1/cotizaciones/cot-004-detalle.pdf',   'pdf'),
  (5, 6, 'https://res.cloudinary.com/agromatina/raw/upload/v1/cotizaciones/cot-006-requisitos.pdf','pdf'),
  (6, 6, 'https://res.cloudinary.com/agromatina/image/upload/v1/cotizaciones/cot-006-area.png',    'png'),
  (7, 6, 'https://res.cloudinary.com/agromatina/image/upload/v1/cotizaciones/cot-006-muestra.jpeg','jpeg');