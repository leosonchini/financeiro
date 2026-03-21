from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from database import db
from models import *
import openpyxl

app = Flask(__name__)
import os
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///financeiro.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'sua-chave-secreta-aqui'

db.init_app(app)

@app.template_filter('moeda')
def moeda_filter(value):
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

@app.before_request
def criar_tabelas():
    db.create_all()


MESES = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março',
    4: 'Abril', 5: 'Maio', 6: 'Junho',
    7: 'Julho', 8: 'Agosto', 9: 'Setembro',
    10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

@app.context_processor
def inject_now():
    hoje = datetime.now()
    mes_nome = MESES[hoje.month]
    return {
        'now': hoje,
        'mes_atual': f"{mes_nome}/{hoje.year}"
    }

@app.route('/')
def painel():
    hoje = datetime.now()
    mes = hoje.month
    ano = hoje.year
    fixas = DespesaFixa.query.filter_by(ativa=True).all()
    for despesa in fixas:
        despesa.pagamento_mes = PagamentoMes.query.filter_by(
            tipo='fixa', referencia_id=despesa.id,
            mes=mes, ano=ano, pago=True
        ).first()
    fixas = sorted(fixas, key=lambda d: (0 if d.pagamento_mes else 1))

    variaveis = DespesaVariavel.query.all()
    for despesa in variaveis:
        despesa.lancamento_mes = LancamentoDespesaVariavel.query.filter_by(
            despesa_id=despesa.id, mes=mes, ano=ano
        ).first()
    variaveis = sorted(variaveis, key=lambda d: (0 if d.lancamento_mes and d.lancamento_mes.pago else 1))

    clientes = Cliente.query.filter_by(status='ativo').all()
    for cliente in clientes:
        cliente.pagamento_mes = PagamentoCliente.query.filter_by(
            cliente_id=cliente.id, mes=mes, ano=ano, pago=True
        ).first()
    clientes = sorted(clientes, key=lambda c: (0 if c.pagamento_mes else 1))

    receitas_fixas = ReceitaPessoal.query.filter_by(fixa=True).all()
    receitas_extras = ReceitaPessoal.query.filter_by(fixa=False).all()
    for extra in receitas_extras:
        extra.lancado_mes = LancamentoReceitaExtra.query.filter_by(
            receita_id=extra.id, mes=mes, ano=ano
        ).first()
    total_receita_fixa = sum(r.valor for r in receitas_fixas)
    total_receita_extra = sum(e.lancado_mes.valor for e in receitas_extras if e.lancado_mes)
    total_clientes = sum(c.valor_mensalidade for c in clientes)
    total_receitas = total_receita_fixa + total_receita_extra + total_clientes
    total_despesas_fixas = sum(d.valor for d in fixas)
    total_despesas_variaveis = sum(d.lancamento_mes.valor for d in variaveis if d.lancamento_mes)
    total_despesas = total_despesas_fixas + total_despesas_variaveis
    pagas_fixas = sum(d.valor for d in fixas if d.pagamento_mes)
    pagas_variaveis = sum(d.lancamento_mes.valor for d in variaveis if d.lancamento_mes and d.lancamento_mes.pago)
    clientes_pagos = sum(c.valor_mensalidade for c in clientes if c.pagamento_mes)
    total_pago = pagas_fixas + pagas_variaveis
    total_recebido = clientes_pagos + total_receita_fixa + total_receita_extra
    saldo_previsto = total_receitas - total_despesas
    saldo_realizado = total_recebido - total_pago
    contas_abertas = []
    for d in fixas:
        if not d.pagamento_mes:
            contas_abertas.append({'nome': d.descricao, 'valor': d.valor, 'tipo': 'Fixa'})
    for d in variaveis:
        if d.lancamento_mes and not d.lancamento_mes.pago:
            contas_abertas.append({'nome': d.descricao, 'valor': d.lancamento_mes.valor, 'tipo': 'Variável'})
    
    return render_template('painel.html',
        mes=MESES[mes], ano=ano,
        total_receitas=total_receitas,
        total_despesas=total_despesas,
        saldo_previsto=saldo_previsto,
        saldo_realizado=saldo_realizado,
        total_pago=total_pago,
        total_recebido=total_recebido,
        contas_abertas=contas_abertas,
        fixas=fixas,
        variaveis=variaveis,
        clientes=clientes
    )

@app.route('/clientes')
def clientes():
    hoje = datetime.now()
    todos = Cliente.query.order_by(Cliente.nome).all()
    for cliente in todos:
        cliente.pagamento_mes = PagamentoCliente.query.filter_by(
            cliente_id=cliente.id,
            mes=hoje.month,
            ano=hoje.year,
            pago=True
        ).first()
    return render_template('clientes.html', clientes=todos)

@app.route('/clientes/novo', methods=['POST'])
def novo_cliente():
    nome = request.form['nome']
    valor = float(request.form['valor'])
    dia = int(request.form['dia_vencimento'])
    cliente = Cliente(nome=nome, valor_mensalidade=valor, dia_vencimento=dia)
    db.session.add(cliente)
    db.session.commit()
    return redirect(url_for('clientes'))

@app.route('/clientes/status/<int:id>', methods=['POST'])
def atualizar_status_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    cliente.status = request.form['status']
    db.session.commit()
    return redirect(url_for('clientes'))

@app.route('/clientes/pagar/<int:id>', methods=['POST'])
def pagar_cliente(id):
    hoje = datetime.now()
    pagamento = PagamentoCliente.query.filter_by(
        cliente_id=id, mes=hoje.month, ano=hoje.year
    ).first()
    if pagamento:
        pagamento.pago = not pagamento.pago
    else:
        pagamento = PagamentoCliente(
            cliente_id=id, mes=hoje.month, ano=hoje.year, pago=True
        )
        db.session.add(pagamento)
    db.session.commit()
    return redirect(url_for('clientes'))

@app.route('/despesas-fixas')
def despesas_fixas():
    hoje = datetime.now()
    despesas = DespesaFixa.query.filter_by(ativa=True).order_by(DespesaFixa.descricao).all()
    for despesa in despesas:
        despesa.pagamento_mes = PagamentoMes.query.filter_by(
            tipo='fixa',
            referencia_id=despesa.id,
            mes=hoje.month,
            ano=hoje.year,
            pago=True
        ).first()
    return render_template('despesas_fixas.html', despesas=despesas)

@app.route('/despesas-fixas/nova', methods=['POST'])
def nova_despesa_fixa():
    descricao = request.form['descricao']
    valor = float(request.form['valor'])
    despesa = DespesaFixa(descricao=descricao, valor=valor)
    db.session.add(despesa)
    db.session.commit()
    return redirect(url_for('despesas_fixas'))

@app.route('/despesas-fixas/pagar/<int:id>', methods=['POST'])
def pagar_despesa_fixa(id):
    hoje = datetime.now()
    pagamento = PagamentoMes.query.filter_by(
        tipo='fixa', referencia_id=id,
        mes=hoje.month, ano=hoje.year
    ).first()
    if pagamento:
        pagamento.pago = not pagamento.pago
    else:
        pagamento = PagamentoMes(
            tipo='fixa', referencia_id=id,
            mes=hoje.month, ano=hoje.year, pago=True
        )
        db.session.add(pagamento)
    db.session.commit()
    return redirect(url_for('despesas_fixas'))

@app.route('/despesas-fixas/editar/<int:id>', methods=['POST'])
def editar_despesa_fixa(id):
    despesa = DespesaFixa.query.get_or_404(id)
    novo_valor = float(request.form['valor'])
    if novo_valor != despesa.valor:
        historico = HistoricoReajuste(
            despesa_id=despesa.id,
            valor_antigo=despesa.valor,
            valor_novo=novo_valor
        )
        db.session.add(historico)
        despesa.valor = novo_valor
    despesa.descricao = request.form['descricao']
    db.session.commit()
    return redirect(url_for('despesas_fixas'))

@app.route('/despesas-fixas/desativar/<int:id>', methods=['POST'])
def desativar_despesa_fixa(id):
    despesa = DespesaFixa.query.get_or_404(id)
    despesa.ativa = False
    db.session.commit()
    return redirect(url_for('despesas_fixas'))

@app.route('/despesas-variaveis')
def despesas_variaveis():
    hoje = datetime.now()
    despesas = DespesaVariavel.query.order_by(DespesaVariavel.descricao).all()
    for despesa in despesas:
        despesa.lancamento_mes = LancamentoDespesaVariavel.query.filter_by(
            despesa_id=despesa.id,
            mes=hoje.month,
            ano=hoje.year
        ).first()
    return render_template('despesas_variaveis.html', despesas=despesas, mes=MESES[hoje.month], ano=hoje.year)

@app.route('/despesas-variaveis/nova', methods=['POST'])
def nova_despesa_variavel():
    descricao = request.form['descricao']
    cor = request.form['cor']
    despesa = DespesaVariavel(descricao=descricao, cor=cor)
    db.session.add(despesa)
    db.session.commit()
    return redirect(url_for('despesas_variaveis'))

@app.route('/despesas-variaveis/lancar/<int:id>', methods=['POST'])
def lancar_despesa_variavel(id):
    hoje = datetime.now()
    valor = float(request.form['valor'])
    lancamento = LancamentoDespesaVariavel.query.filter_by(
        despesa_id=id, mes=hoje.month, ano=hoje.year
    ).first()
    if lancamento:
        lancamento.valor = valor
    else:
        lancamento = LancamentoDespesaVariavel(
            despesa_id=id, mes=hoje.month, ano=hoje.year, valor=valor, pago=False
        )
        db.session.add(lancamento)
    db.session.commit()
    return redirect(url_for('despesas_variaveis'))

@app.route('/despesas-variaveis/pagar/<int:id>', methods=['POST'])
def pagar_despesa_variavel(id):
    hoje = datetime.now()
    lancamento = LancamentoDespesaVariavel.query.filter_by(
        despesa_id=id, mes=hoje.month, ano=hoje.year
    ).first()
    if lancamento:
        lancamento.pago = not lancamento.pago
        db.session.commit()
        if lancamento.pago:
            parcelas = CompraParcelada.query.filter_by(despesa_variavel_id=id).all()
            for compra in parcelas:
                parcela_mes = ParcelaMes.query.filter_by(
                    compra_id=compra.id, mes=hoje.month, ano=hoje.year
                ).first()
                if not parcela_mes:
                    parcela_mes = ParcelaMes(
                        compra_id=compra.id, mes=hoje.month, ano=hoje.year, pago=True
                    )
                    db.session.add(parcela_mes)
                else:
                    parcela_mes.pago = True
            db.session.commit()
    return redirect(url_for('despesas_variaveis'))

@app.route('/despesas-variaveis/excluir/<int:id>', methods=['POST'])
def excluir_despesa_variavel(id):
    despesa = DespesaVariavel.query.get_or_404(id)
    LancamentoDespesaVariavel.query.filter_by(despesa_id=id).delete()
    CompraParcelada.query.filter_by(despesa_variavel_id=id).delete()
    db.session.delete(despesa)
    db.session.commit()
    return redirect(url_for('despesas_variaveis'))

@app.route('/parcelas')
def parcelas():
    hoje = datetime.now()
    todas = CompraParcelada.query.order_by(CompraParcelada.descricao).all()
    despesas_variaveis = DespesaVariavel.query.order_by(DespesaVariavel.descricao).all()
    total_restante = 0
    for compra in todas:
        pagas = ParcelaMes.query.filter_by(compra_id=compra.id, pago=True).count()
        compra.parcelas_pagas = pagas
        compra.parcelas_restantes = compra.num_parcelas - pagas
        compra.valor_restante = compra.parcelas_restantes * compra.valor_parcela
        total_restante += compra.valor_restante
        if compra.despesa_variavel_id:
            compra.cartao = DespesaVariavel.query.get(compra.despesa_variavel_id)
        else:
            compra.cartao = None
    return render_template('parcelas.html',
        parcelas=todas,
        despesas_variaveis=despesas_variaveis,
        total_restante=total_restante,
        mes=MESES[hoje.month],
        ano=hoje.year
    )

@app.route('/parcelas/nova', methods=['POST'])
def nova_parcela():
    descricao = request.form['descricao']
    valor_parcela = float(request.form['valor_parcela'])
    num_parcelas = int(request.form['num_parcelas'])
    mes_inicio = int(request.form['mes_inicio'])
    ano_inicio = int(request.form['ano_inicio'])
    despesa_variavel_id = int(request.form['despesa_variavel_id'])
    compra = CompraParcelada(
        descricao=descricao,
        valor_parcela=valor_parcela,
        num_parcelas=num_parcelas,
        mes_inicio=mes_inicio,
        ano_inicio=ano_inicio,
        despesa_variavel_id=despesa_variavel_id
    )
    db.session.add(compra)
    db.session.commit()
    return redirect(url_for('parcelas'))

@app.route('/parcelas/excluir/<int:id>', methods=['POST'])
def excluir_parcela(id):
    compra = CompraParcelada.query.get_or_404(id)
    ParcelaMes.query.filter_by(compra_id=id).delete()
    db.session.delete(compra)
    db.session.commit()
    return redirect(url_for('parcelas'))

@app.route('/receitas')
def receitas():
    hoje = datetime.now()
    fixas = ReceitaPessoal.query.filter_by(fixa=True).order_by(ReceitaPessoal.descricao).all()
    extras = ReceitaPessoal.query.filter_by(fixa=False).all()
    for extra in extras:
        extra.lancado_mes = LancamentoReceitaExtra.query.filter_by(
            receita_id=extra.id,
            mes=hoje.month,
            ano=hoje.year
        ).first()
    clientes_ativos = Cliente.query.filter_by(status='ativo').all()
    for cliente in clientes_ativos:
        cliente.pagamento_mes = PagamentoCliente.query.filter_by(
            cliente_id=cliente.id,
            mes=hoje.month,
            ano=hoje.year,
            pago=True
        ).first()
    total_fixo = sum(r.valor for r in fixas)
    total_extra = sum(e.lancado_mes.valor for e in extras if e.lancado_mes)
    total_clientes = sum(c.valor_mensalidade for c in clientes_ativos)
    return render_template('receitas.html',
        fixas=fixas,
        extras=extras,
        clientes=clientes_ativos,
        total_fixo=total_fixo,
        total_extra=total_extra,
        total_clientes=total_clientes,
        total_geral=total_fixo + total_extra + total_clientes,
        mes=MESES[hoje.month],
        ano=hoje.year
    )

@app.route('/receitas/nova-fixa', methods=['POST'])
def nova_receita_fixa():
    descricao = request.form['descricao']
    valor = float(request.form['valor'])
    receita = ReceitaPessoal(descricao=descricao, valor=valor, fixa=True)
    db.session.add(receita)
    db.session.commit()
    return redirect(url_for('receitas'))

@app.route('/receitas/nova-extra', methods=['POST'])
def nova_receita_extra():
    descricao = request.form['descricao']
    receita = ReceitaPessoal(descricao=descricao, valor=0, fixa=False)
    db.session.add(receita)
    db.session.commit()
    return redirect(url_for('receitas'))

@app.route('/receitas/lancar-extra/<int:id>', methods=['POST'])
def lancar_receita_extra(id):
    hoje = datetime.now()
    valor = float(request.form['valor'])
    lancamento = LancamentoReceitaExtra.query.filter_by(
        receita_id=id, mes=hoje.month, ano=hoje.year
    ).first()
    if lancamento:
        lancamento.valor = valor
    else:
        lancamento = LancamentoReceitaExtra(
            receita_id=id, mes=hoje.month, ano=hoje.year, valor=valor
        )
        db.session.add(lancamento)
    db.session.commit()
    return redirect(url_for('receitas'))

@app.route('/receitas/editar-fixa/<int:id>', methods=['POST'])
def editar_receita_fixa(id):
    receita = ReceitaPessoal.query.get_or_404(id)
    receita.descricao = request.form['descricao']
    receita.valor = float(request.form['valor'])
    db.session.commit()
    return redirect(url_for('receitas'))

@app.route('/receitas/excluir/<int:id>', methods=['POST'])
def excluir_receita(id):
    receita = ReceitaPessoal.query.get_or_404(id)
    db.session.delete(receita)
    db.session.commit()
    return redirect(url_for('receitas'))

@app.route('/importar', methods=['GET', 'POST'])
def importar():
    if request.method == 'GET':
        return render_template('importar.html')
    arquivo = request.files['arquivo']
    if not arquivo:
        return redirect(url_for('importar'))
    wb = openpyxl.load_workbook(arquivo)
    resultado = {'clientes': 0, 'despesas': 0, 'erros': []}
    if 'RECEITAS' in wb.sheetnames:
        ws = wb['RECEITAS']
        rows = list(ws.iter_rows(values_only=True))
        for row in rows[1:]:
            if not row[0]:
                continue
            nome = str(row[0]).strip()
            if not nome:
                continue
            try:
                dia = int(row[1]) if row[1] else 1
                valor = float(row[2]) if row[2] else 0
                existente = Cliente.query.filter_by(nome=nome).first()
                if not existente:
                    cliente = Cliente(
                        nome=nome,
                        valor_mensalidade=valor,
                        dia_vencimento=dia,
                        status='ativo'
                    )
                    db.session.add(cliente)
                    resultado['clientes'] += 1
            except Exception as e:
                resultado['erros'].append(f"Cliente {nome}: {str(e)}")
    if 'DESPESAS' in wb.sheetnames:
        ws = wb['DESPESAS']
        rows = list(ws.iter_rows(values_only=True))
        header = rows[0]
        meses_colunas = []
        for i, cell in enumerate(header):
            if isinstance(cell, datetime):
                meses_colunas.append((i, cell))
        for row in rows[1:]:
            if not row[0]:
                continue
            nome = str(row[0]).strip()
            if not nome:
                continue
            tipo = str(row[1]).strip().lower() if row[1] else 'v'
            try:
                if tipo == 'f':
                    valor_fixo = 0
                    for col_idx, mes_data in meses_colunas:
                        val = row[col_idx]
                        if val and isinstance(val, (int, float)) and val > 0:
                            valor_fixo = float(val)
                            break
                    existente = DespesaFixa.query.filter_by(descricao=nome).first()
                    if not existente:
                        despesa = DespesaFixa(descricao=nome, valor=valor_fixo, ativa=True)
                        db.session.add(despesa)
                    resultado['despesas'] += 1
                else:
                    existente = DespesaVariavel.query.filter_by(descricao=nome).first()
                    if not existente:
                        despesa = DespesaVariavel(descricao=nome, cor='#f1efe8')
                        db.session.add(despesa)
                        db.session.flush()
                    else:
                        despesa = existente
                    for col_idx, mes_data in meses_colunas:
                        valor = row[col_idx]
                        if valor and isinstance(valor, (int, float)) and valor > 0:
                            mes = mes_data.month
                            ano = mes_data.year
                            lanc_existente = LancamentoDespesaVariavel.query.filter_by(
                                despesa_id=despesa.id, mes=mes, ano=ano
                            ).first()
                            if not lanc_existente:
                                lanc = LancamentoDespesaVariavel(
                                    despesa_id=despesa.id,
                                    mes=mes, ano=ano,
                                    valor=float(valor),
                                    pago=False
                                )
                                db.session.add(lanc)
                    resultado['despesas'] += 1
            except Exception as e:
                resultado['erros'].append(f"Despesa {nome}: {str(e)}")
    db.session.commit()
    return render_template('importar.html', resultado=resultado)

@app.route('/despesas-variaveis/cor/<int:id>', methods=['POST'])
def editar_cor_despesa_variavel(id):
    despesa = DespesaVariavel.query.get_or_404(id)
    despesa.cor = request.form['cor']
    db.session.commit()
    return redirect(url_for('despesas_variaveis'))

@app.route('/despesas-variaveis/editar/<int:id>', methods=['POST'])
def editar_despesa_variavel(id):
    despesa = DespesaVariavel.query.get_or_404(id)
    despesa.descricao = request.form['descricao']
    db.session.commit()
    return redirect(url_for('despesas_variaveis'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)