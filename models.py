from datetime import datetime
from database import db

class ReceitaPessoal(db.Model):
    __tablename__ = 'receita_pessoal'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    fixa = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

class Cliente(db.Model):
    __tablename__ = 'cliente'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    valor_mensalidade = db.Column(db.Float, nullable=False)
    dia_vencimento = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='ativo')
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

class DespesaFixa(db.Model):
    __tablename__ = 'despesa_fixa'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    ativa = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

class HistoricoReajuste(db.Model):
    __tablename__ = 'historico_reajuste'
    id = db.Column(db.Integer, primary_key=True)
    despesa_id = db.Column(db.Integer, db.ForeignKey('despesa_fixa.id'), nullable=False)
    valor_antigo = db.Column(db.Float, nullable=False)
    valor_novo = db.Column(db.Float, nullable=False)
    alterado_em = db.Column(db.DateTime, default=datetime.utcnow)

class DespesaVariavel(db.Model):
    __tablename__ = 'despesa_variavel'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    cor = db.Column(db.String(20), default='#f1efe8')
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

class LancamentoDespesaVariavel(db.Model):
    __tablename__ = 'lancamento_despesa_variavel'
    id = db.Column(db.Integer, primary_key=True)
    despesa_id = db.Column(db.Integer, db.ForeignKey('despesa_variavel.id'), nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    valor = db.Column(db.Float, nullable=False)
    pago = db.Column(db.Boolean, default=False)


class CompraParcelada(db.Model):
    __tablename__ = 'compra_parcelada'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    valor_parcela = db.Column(db.Float, nullable=False)
    num_parcelas = db.Column(db.Integer, nullable=False)
    mes_inicio = db.Column(db.Integer, nullable=False)
    ano_inicio = db.Column(db.Integer, nullable=False)
    despesa_variavel_id = db.Column(db.Integer, db.ForeignKey('despesa_variavel.id'), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

class ParcelaMes(db.Model):
    __tablename__ = 'parcela_mes'
    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('compra_parcelada.id'), nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    pago = db.Column(db.Boolean, default=False)

class PagamentoMes(db.Model):
    __tablename__ = 'pagamento_mes'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)
    referencia_id = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    pago = db.Column(db.Boolean, default=False)

class PagamentoCliente(db.Model):
    __tablename__ = 'pagamento_cliente'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    pago = db.Column(db.Boolean, default=False)

class LancamentoReceitaExtra(db.Model):
    __tablename__ = 'lancamento_receita_extra'
    id = db.Column(db.Integer, primary_key=True)
    receita_id = db.Column(db.Integer, db.ForeignKey('receita_pessoal.id'), nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    valor = db.Column(db.Float, nullable=False)