#coding=utf-8
from django.shortcuts import render,redirect,render_to_response
from django.core.urlresolvers import reverse
from shopcart.models import System_Config,Express,Order,OrderRemark,ExpressType,OrderShippment
from shopcart.utils import my_pagination,get_serial_number,get_system_parameters
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse,JsonResponse,Http404
from django.template.response import TemplateResponse
import logging,json
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.utils.translation import ugettext as _
from django.db import transaction
from shopcart.myadmin.utils import NO_PERMISSION_PAGE


# Get an instance of a logger
import logging
logger = logging.getLogger('icetus.shopcart')

def get_page_size():
	try:
		size = System_Config.objects.get(name='admin_order_list_page_size').val
	except:
		logger.info('"admin_order_list_page_size" is not setted.Use default value 12.')
		size = 12
	return size

@staff_member_required
def detail(request,id=None):
	ctx = {}
	ctx['system_para'] = get_system_parameters()
	ctx['page_name'] = 'Order Detail'
	try:
		order = Order.objects.get(id=id)
	except Exception as err:
		logger.error("Can not find order which id is %s" % id)
		raise Http404	
	
	ctx['order'] = order
	return TemplateResponse(request,System_Config.get_template_name('admin') + '/order_detail.html',ctx)
		

@staff_member_required
@permission_required('shopcart.can_list_order', login_url=NO_PERMISSION_PAGE)
def list_view(request):
	ctx = {}
	ctx['system_para'] = get_system_parameters()
	ctx['page_name'] = '订单管理'
	
	if request.method == 'GET':
		query_item = request.GET.get('query_item','')
		ctx['query_item'] = query_item
		
		logger.debug('query item : %s' % query_item)
		
		item_value = request.GET.get('item_value','')
		ctx['item_value'] = item_value
		query_status = request.GET.get('query_status','')
		ctx['query_status'] = query_status
		
		#all = Order.objects.all().order_by('-update_time')
		all = Order.objects.all().order_by('-create_time')
		
		if query_item == 'order_number':
			if item_value:
				all = all.filter(order_number=item_value)
		elif query_item == 'order_user_email':
			if item_value:
				all = all.filter(user__email=item_value)
		else:
			pass
		
		if query_status:
			all = all.filter(status=query_status)
		
		

		page_size = get_page_size()
		order_list, page_range = my_pagination(request=request, queryset=all,display_amount=page_size)
		
		ctx['order_list'] = order_list
		ctx['page_range'] = page_range
		ctx['page_size'] = page_size
		ctx['order_count'] = all.count()
		return TemplateResponse(request,System_Config.get_template_name('admin') + '/order_list_content.html',ctx)
	else:
		raise Http404

		
'''		
@staff_member_required
@transaction.atomic()
###由于发货已经改成记录明细了，所以这个方法不需要了
def ship(request):	
	result_dict = {}
	message_dict = {}
	if request.method == 'POST':
		order_id = request.POST.get('order_id','')
		express_id = request.POST.get('express_id','')
		shpping_no = request.POST.get('shpping_no','')
		try:
			order = Order.objects.get(id=order_id)
			express = Express.objects.get(id=express_id)
		except:
			logger.error('Can not find order which id is %s' % (order_id))
			raise Http404
		
		order.shpping_no = shipping_no
		order.shipper_name = express.name
		order.status = Order.ORDER_STATUS_SHIPPING
		order.save()
				
		result_dict['success'] = True
		message_dict['status'] = _('已发货')
		result_dict['message'] = message_dict
		return JsonResponse(result_dict)
		
	else:
		raise Http404		
'''		
		
		
@staff_member_required
@transaction.atomic()
def remark_add(request):
	result_dict = {}
	if request.method == 'POST':
		try:
			order_id = request.POST.get('order_id','')
			order = Order.objects.get(id=order_id)
			content = request.POST.get('content','')
			user = request.user
			order_remark = OrderRemark.objects.create(order=order,content=content,user=user)
			result_dict['success'] = True
			result_dict['message'] = '订单备注保存成功'
		except Exception as err:
			logger.error('Save OrderRemark which id is [%s] faild. \n Error Message:%s' %(order_id,err))
			result_dict['success'] = False
			result_dict['message'] = '订单备注保存失败'
		return JsonResponse(result_dict)
	else:
		ctx = {}
		ctx['system_para'] = get_system_parameters()
		ctx['page_name'] = '发货管理'
		
		order_id = request.GET.get('order_id','')
		ctx['order_id'] = order_id
		return TemplateResponse(request,System_Config.get_template_name('admin') + '/order_remark.html',ctx)
		
@staff_member_required
@transaction.atomic()		
def ship_out(request):
	result_dict = {}
	if request.method == 'POST':
		#logger.debug('request.POST:%s' % request.POST)
	
		try:
			order_id = request.POST.get('order_id','')
			order = Order.objects.get(id=order_id)
		except Exception as err:
			logger.error('Save shippment which id is [%s] faild. \n Error Message:%s' %(order_id,err))
			result_dict['success'] = False
			result_dict['message'] = '订单号为%s的订单找不到！' % order_id
			return JsonResponse(result_dict)
		
		try:
			express_id = request.POST.get('express_id','')
			express = Express.objects.get(id = express_id)
		except Exception as err:
			logger.error('Save shippment which id is [%s] faild. Because of the express which id is %s can not be found. \n Error Message:%s' %(order_id,express_id,err))
			result_dict['success'] = False
			result_dict['message'] = 'ID号为%s的快递公司找不到！' % express_id
			return JsonResponse(result_dict)
		
		from shopcart.forms import order_shippment_form
		form = order_shippment_form(request.POST)
		if form.is_valid():
			order_shippment = form.save()
			order_shippment.order = order
			order_shippment.shipper_name = express.name
			order_shippment.express = express
			order_shippment.save()
			#修改订单状态
			is_all_shipped = request.POST.get('is_all_shipped','true')
			if is_all_shipped == 'false':
				order.status = Order.ORDER_STATUS_PART_SHIPPING
			else:	
				order.status = Order.ORDER_STATUS_SHIPPING
			order.save()
			
			result_dict['success'] = True
			result_dict['message'] = '发货成功'
			return JsonResponse(result_dict)
		else:
			result_dict['success'] = False
			result_dict['message'] = '表单填写的内容不合法，请检查。'
			return JsonResponse(result_dict)
	else:
		ctx = {}
		ctx['system_para'] = get_system_parameters()
		ctx['page_name'] = '发货管理'
		
		order_id = request.GET.get('order_id','')
		try:
			order = Order.objects.get(id=order_id)
		except Exception as err:
			logger.error('Can not find order [%s]. \n Error Message:%s' %(order_id,err))
			raise Http404
			
		#快递列表
		express_list = Express.objects.filter(is_in_use=True).filter(is_delete=False)
		express_type_list = ExpressType.objects.filter(is_in_use=True).filter(is_delete=False)
		ctx['express_type_list'] = express_type_list	
		
		express_list_result = express_list
		if order.express_type_id != 0 :
			try:
				logger.debug("1.1")
				express_list_result = express_list.filter(express_type=order.express_type_id)
				logger.debug("1.2 : %s " % express_list_result)
			except Exception as err:
				logger.debug('1.3 : %s ' % err)
				
				
		ctx['express_list'] = express_list_result	
			
		ctx['order'] = order
		return TemplateResponse(request,System_Config.get_template_name('admin') + '/order_shippment_detail.html',ctx)


@staff_member_required
@transaction.atomic()		
def price_adjusment(request):
	result_dict = {}
	if request.method == 'POST':
		order_id = request.POST.get('order_id','')
		price = request.POST.get('price_adjusment','0')
		
		logger.debug('price_adjusment:%s' % price)
		
		try:
			order = Order.objects.get(id=order_id)
			price = float(price)
		except Exception as err:
			logger.error('Can not find order [%s] \n Error Message:%s' %(order_id,err))
			result_dict['success'] = False
			result_dict['message'] = '价格调整失败'
			return JsonResponse(result_dict)
		
		
		order.price_adjusment = price
		order.calculate_total_price()
		order.save()
		result_dict['success'] = True
		result_dict['message'] = '价格调整成功'
		return JsonResponse(result_dict)
	else:
		ctx = {}
		ctx['system_para'] = get_system_parameters()
		ctx['page_name'] = '价格调整'
		ctx['order_id'] = request.GET.get('order_id')
		return TemplateResponse(request,System_Config.get_template_name('admin') + '/order_price_adjusment.html',ctx)
			
			

@staff_member_required
@transaction.atomic()		
def shipment_delete(request,id):
	result_dict = {}
	if request.method == 'POST':
		try:
			shipment = OrderShippment.objects.get(id=id)
		except Exception as err:
			logger.error('Can not find shippment which id is [%s]. \n Error Message:%s' %(id,err))
			result_dict['success'] = False
			result_dict['message'] = 'ID号为%s的发货记录找不到！' % id
			return JsonResponse(result_dict)
		
		shipment.delete()
		result_dict['success'] = True
		result_dict['message'] = '删除成功'
		return JsonResponse(result_dict)
	else:
		result_dict['success'] = False
		result_dict['message'] = '表单填写的内容不合法，请检查。'
		return JsonResponse(result_dict)			
			
			
		
@staff_member_required
@transaction.atomic()
def modify_status(request,status='',order_id=''):
	result_dict = {}
	result_dict['success'] = False
	result_dict['message'] = '表单填写的内容不合法，请检查。'
	if request.method == 'POST':
		if order_id:
			try:
				order = Order.objects.get(id=order_id)
			except Exception as err:
				logger.error('Can not find the order which id is [%s].' % order_id)
				
			if order:	
				if status == 'collected':
					if order.status == Order.ORDER_STATUS_PAYED_SUCCESS:
						#已有在付款已确认状态下，才可以备货
						order.status = Order.ORDER_STATUS_COLLECT_SUCCESS
						order.save()
						result_dict['success'] = True
						result_dict['message'] = '订单备货完成'
					else:
						result_dict['message'] = '订单当前状态不是“付款已确认状态”，不能进行备货操作。' 
				elif status == 'closed':
					#订单在任何情况下都可以关闭，权限很大
					order.status = Order.ORDER_STATUS_CLOSED
					order.save()
					result_dict['success'] = True
					result_dict['message'] = '订单成功关闭'
				elif status == 'finished':
					if order.status == Order.ORDER_STATUS_SHIPPING:
						#只有在已经发货的状态下，才可以结束订单
						order.status = Order.ORDER_STATUS_COMPLETE
						order.save()
						result_dict['success'] = True
						result_dict['message'] = '订单成功完结'
					else:
						result_dict['message'] = '订单当前状态不是“已发货”状态，不得进行完成操作。'
				else:
					logger.info('Order Status arguments is not valid. The value is [%s].' % status)
	return JsonResponse(result_dict)
				
@staff_member_required
def oper(request):	
	if request.method == 'POST':
		oper_ids = request.POST.get('oper-ids','')
		if oper_ids == '':
			raise Http404
		else:
			oper_id_list = oper_ids.split(',')
			for id in oper_id_list:
				try:
					order = Order.objects.get(id=id)
					order.delete()
				except:
					logger.info('Can not find order which id is %s to delete.' % (id))
		return redirect('/admin/order-list/')
	else:
		raise Http404
