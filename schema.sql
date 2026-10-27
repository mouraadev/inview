CREATE TABLE IF NOT EXISTS documentos (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
    nome_original VARCHAR(255) NOT NULL,
    conteudo MEDIUMBLOB NOT NULL,
    extracao JSON NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS faturas (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    documento_id BIGINT NOT NULL UNIQUE,
    fornecedor VARCHAR(255) NOT NULL,
    identificador_fiscal VARCHAR(255),
    numero_fatura VARCHAR(255) NOT NULL,
    data_emissao DATE NOT NULL,
    data_vencimento DATE,
    moeda CHAR(3) NOT NULL,
    total DECIMAL(18,2) NOT NULL,
    subtotal DECIMAL(18,2),
    desconto DECIMAL(18,2),
    tributos DECIMAL(18,2),
    pedido_compra VARCHAR(255),
    chave_negocio CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    revisao JSON NOT NULL,
    confirmado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (documento_id) REFERENCES documentos(id),
    INDEX idx_negocio (chave_negocio),
    INDEX idx_emissao_moeda (data_emissao, moeda),
    INDEX idx_vencimento (data_vencimento),
    CHECK (total >= 0),
    CHECK (moeda IN ('BRL', 'USD', 'EUR'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
